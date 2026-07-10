"""数据采集API路由"""

import logging
import asyncio
import json
import os
from pathlib import Path
from threading import Lock
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from pydantic import BaseModel
from backend.schemas.models import ApiResponse, CollectionRequest, CollectionResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/data", tags=["数据采集"])

# ===== 全局采集任务状态 =====
_collection_status = {
    "running": False,
    "phase": "",           # collecting | building_graph | done
    "current_keyword": "",
    "completed_keywords": [],
    "result": None,
    "build_result": None,  # 图谱构建结果
    "error": None,
    "started_at": None,
}
_status_lock = Lock()


# ===== 外部数据导入请求模型 =====
class ImportDataRequest(BaseModel):
    """外部数据导入请求"""
    jobs: list[dict]  # 岗位数据列表
    skip_llm_enhance: bool = False  # 是否跳过LLM增强（如果数据已包含技能）


class ImportDataResponse(BaseModel):
    """导入结果"""
    success: bool
    message: str
    total_imported: int
    skills_extracted: int
    jobs_created: int
    relations_created: int


def _run_collection():
    """在后台线程中执行：采集数据 + 自动构建图谱（不阻塞请求线程）"""
    global _collection_status

    # ===== 阶段1：数据采集 =====
    try:
        with _status_lock:
            _collection_status["phase"] = "collecting"

        from agents.data_collector import DataCollectorAgent
        agent = DataCollectorAgent()
        result = agent.collect_all_sources()

        logger.info(f"阶段1完成 - 数据采集: {result.get('total_deduplicated', 0)}条")

    except Exception as e:
        logger.error(f"后台数据采集失败: {e}")
        with _status_lock:
            _collection_status["running"] = False
            _collection_status["phase"] = "done"
            _collection_status["error"] = f"采集失败: {e}"
        return

    # ===== 阶段2：构建图谱（将采集的数据写入Neo4j） =====
    try:
        with _status_lock:
            _collection_status["phase"] = "building_graph"
            _collection_status["current_keyword"] = "正在构建知识图谱..."

        from agents.graph_builder import GraphBuilderAgent
        builder = GraphBuilderAgent()
        processed_data = result.get("processed_data", [])
        build_result = builder.build_from_data(processed_data)

        with _status_lock:
            _collection_status["build_result"] = build_result
            _collection_status["result"] = result
            _collection_status["running"] = False
            _collection_status["phase"] = "done"
            _collection_status["current_keyword"] = ""
            _collection_status["error"] = None

        logger.info(f"阶段2完成 - 图谱构建: +{build_result.get('skills_added', 0)}技能, "
                     f"+{build_result.get('jobs_updated', 0)}岗位, "
                     f"+{build_result.get('relations_created', 0)}关系")

    except Exception as e:
        logger.error(f"图谱构建失败（采集已完成）: {e}")
        with _status_lock:
            _collection_status["result"] = result  # 保留采集结果
            _collection_status["running"] = False
            _collection_status["phase"] = "done"
            _collection_status["error"] = f"采集成功但图谱构建失败: {e}"


@router.post("/collect", response_model=ApiResponse)
async def collect_data(request: CollectionRequest, background_tasks: BackgroundTasks):
    """触发多源数据采集（异步后台执行，立即返回）"""
    global _collection_status

    with _status_lock:
        if _collection_status["running"]:
            raise HTTPException(status_code=409, detail="数据采集正在进行中，请稍后再试")

        _collection_status = {
            "running": True,
            "current_keyword": "初始化中...",
            "completed_keywords": [],
            "result": None,
            "error": None,
            "started_at": __import__('datetime').datetime.now().isoformat(),
        }

    # 放入后台线程池执行，不阻塞当前请求
    background_tasks.add_task(_run_collection)

    return ApiResponse(
        success=True,
        message="数据采集任务已启动，请在系统管理页面查看进度",
        data={"status": "started", "message": "正在后台执行数据采集..."},
    )


@router.get("/collect/status", response_model=ApiResponse)
async def get_collection_status():
    """查询当前数据采集任务状态（供前端轮询）"""
    with _status_lock:
        status_copy = dict(_collection_status)
        # 不返回完整 result（太大），只返回摘要
        if status_copy.get("result"):
            r = status_copy["result"]
            status_copy["result_summary"] = {
                "total_raw": r.get("total_raw", 0),
                "total_deduplicated": r.get("total_deduplicated", 0),
                "sources": r.get("sources", {}),
            }
            del status_copy["result"]
        # 构建结果摘要
        if status_copy.get("build_result"):
            br = status_copy["build_result"]
            status_copy["build_summary"] = {
                "skills_added": br.get("skills_added", 0),
                "jobs_updated": br.get("jobs_updated", 0),
                "relations_created": br.get("relations_created", 0),
            }
            del status_copy["build_result"]
    return ApiResponse(data=status_copy)


@router.get("/sources", response_model=ApiResponse)
async def get_available_sources():
    """获取可用数据源列表"""
    from models.job_model import JobPostSource

    sources = [
        {"name": s.value, "description": f"{s.value}数据源"}
        for s in JobPostSource
    ]

    return ApiResponse(data={"sources": sources})


@router.get("/stats", response_model=ApiResponse)
async def get_collection_stats():
    """获取采集和图谱统计信息"""
    from agents.data_collector import DataCollectorAgent

    agent = DataCollectorAgent()
    try:
        sources_info = {}
        for name, collector in agent.collectors.items():
            sources_info[name] = {
                "is_connected": collector is not None,
                "last_collect_count": 0,
            }
        stats = {"agent_ready": True, "sources": sources_info}
    except Exception:
        stats = {"agent_ready": False}

    try:
        from core.graph_service import get_graph_service
        graph = get_graph_service()
        if not graph.is_connected:
            graph.connect()
        graph_stats = graph.get_graph_stats()
        stats["graph"] = graph_stats
    except Exception as e:
        stats["graph"] = {"error": str(e)}

    return ApiResponse(data=stats)


# ===== 外部数据导入接口 =====

@router.post("/import", response_model=ApiResponse)
async def import_external_data(request: ImportDataRequest):
    """
    导入外部采集的原始数据
    
    数据将经过完整处理流程:
    1. 数据清洗（HTML标签、特殊字符、标准化）
    2. 数据去重（基于标题哈希）
    3. LLM增强（推断技能、薪资范围）
    4. 构建知识图谱（创建节点和关系）
    5. 存入数据库
    
    数据格式要求:
    {
        "jobs": [
            {
                "job_title": "AI算法工程师",       // 必填
                "company_name": "某某公司",         // 可选
                "salary_min": 25,                  // 可选
                "salary_max": 45,                  // 可选
                "location": "北京",                // 可选
                "skills": ["Python", "PyTorch"],   // 可选，如无则LLM推断
                "job_description": "...",         // 可选
                "source": "external_collector",    // 可选
                "source_url": "https://..."        // 可选
            }
        ],
        "skip_llm_enhance": false  // 是否跳过LLM增强
    }
    """
    try:
        jobs = request.jobs
        if not jobs:
            raise HTTPException(status_code=400, detail="jobs列表不能为空")
        
        logger.info(f"开始导入外部原始数据: {len(jobs)}条")
        
        # ===== 第1步：数据清洗 =====
        logger.info("第1步：数据清洗...")
        from core.data_pipeline import DataPipeline
        pipeline = DataPipeline()
        
        cleaned_jobs = []
        for job in jobs:
            # 使用项目的数据清洗流程
            cleaned = pipeline.clean_job_data({
                "job_title": job.get("job_title", ""),
                "company_name": job.get("company_name", ""),
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "location": job.get("location", ""),
                "skills": job.get("skills", []),
                "job_description": job.get("job_description", ""),
                "source": job.get("source", "external_collector"),
                "source_url": job.get("source_url", ""),
            })
            if cleaned and cleaned.get("job_title"):
                cleaned_jobs.append(cleaned)
        
        logger.info(f"数据清洗完成: {len(cleaned_jobs)}/{len(jobs)}条有效")
        
        # ===== 第2步：数据去重 =====
        logger.info("第2步：数据去重...")
        deduplicated_jobs = pipeline.deduplicate_jobs(cleaned_jobs)
        logger.info(f"数据去重完成: {len(deduplicated_jobs)}/{len(cleaned_jobs)}条唯一")
        
        # ===== 第3步：LLM增强 =====
        if not request.skip_llm_enhance:
            logger.info("第3步：LLM增强（推断技能）...")
            from core.llm_service import LLMService
            llm = LLMService()
            
            enhanced_count = 0
            for job in deduplicated_jobs:
                if not job.get("skills") and job.get("job_title"):
                    try:
                        # 使用项目的LLM增强流程
                        result = llm.structured_extraction(
                            text=f"岗位: {job['job_title']}\n描述: {job.get('job_description', '')[:500]}",
                            extraction_schema={
                                "skills": {"type": "array", "description": "该岗位需要的核心技能列表"},
                                "salary_min": {"type": "number", "description": "最低年薪(万)"},
                                "salary_max": {"type": "number", "description": "最高年薪(万)"},
                            },
                            system_prompt="你是招聘领域专家，根据岗位信息推断所需技能和薪资范围。"
                        )
                        if result:
                            if result.get("skills"):
                                job["skills"] = result["skills"][:10]
                                enhanced_count += 1
                            if not job.get("salary_min") and result.get("salary_min"):
                                job["salary_min"] = result["salary_min"]
                            if not job.get("salary_max") and result.get("salary_max"):
                                job["salary_max"] = result["salary_max"]
                    except Exception as e:
                        logger.warning(f"LLM增强失败 [{job['job_title']}]: {e}")
            
            logger.info(f"LLM增强完成: {enhanced_count}条岗位补充了技能")
        
        # ===== 第4步：构建知识图谱 =====
        logger.info("第4步：构建知识图谱...")
        from agents.graph_builder import GraphBuilderAgent
        builder = GraphBuilderAgent()
        build_result = builder.build_from_data(deduplicated_jobs)
        
        # ===== 第5步：保存导入记录 =====
        import_dir = Path("data/import")
        import_dir.mkdir(parents=True, exist_ok=True)
        
        import_record = {
            "imported_at": __import__('datetime').datetime.now().isoformat(),
            "total_raw": len(jobs),
            "total_cleaned": len(cleaned_jobs),
            "total_deduplicated": len(deduplicated_jobs),
            "build_result": build_result,
        }
        
        record_file = import_dir / f"import_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(record_file, "w", encoding="utf-8") as f:
            json.dump({
                "record": import_record,
                "jobs": deduplicated_jobs,
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"外部数据导入完成: 原始{len(jobs)}条 → 清洗{len(cleaned_jobs)}条 → 去重{len(deduplicated_jobs)}条")
        logger.info(f"图谱构建: +{build_result.get('skills_added', 0)}技能, "
                    f"+{build_result.get('jobs_updated', 0)}岗位, "
                    f"+{build_result.get('relations_created', 0)}关系")
        
        return ApiResponse(
            success=True,
            message=f"成功导入 {len(deduplicated_jobs)} 条岗位数据（原始{len(jobs)}条，清洗{len(cleaned_jobs)}条）",
            data={
                "total_raw": len(jobs),
                "total_cleaned": len(cleaned_jobs),
                "total_deduplicated": len(deduplicated_jobs),
                "skills_added": build_result.get("skills_added", 0),
                "jobs_updated": build_result.get("jobs_updated", 0),
                "relations_created": build_result.get("relations_created", 0),
                "record_file": str(record_file),
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导入外部数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.post("/import/file", response_model=ApiResponse)
async def import_from_file(file: UploadFile = File(...)):
    """
    通过文件导入外部采集的数据
    
    支持JSON格式文件，内容格式:
    {
        "jobs": [
            {"job_title": "...", "skills": [...], ...}
        ]
    }
    """
    try:
        # 读取文件内容
        content = await file.read()
        
        # 解析JSON
        try:
            data = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"JSON解析失败: {e}")
        
        # 检查格式
        if isinstance(data, dict):
            jobs = data.get("jobs", [])
            skip_llm = data.get("skip_llm_enhance", False)
        elif isinstance(data, list):
            jobs = data
            skip_llm = False
        else:
            raise HTTPException(status_code=400, detail="数据格式错误，需要对象或数组")
        
        # 调用导入接口
        request = ImportDataRequest(jobs=jobs, skip_llm_enhance=skip_llm)
        return await import_external_data(request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件导入失败: {e}")
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/import/template", response_model=ApiResponse)
async def get_import_template():
    """获取数据导入模板"""
    template = {
        "jobs": [
            {
                "job_title": "AI算法工程师",
                "company_name": "示例公司",
                "salary_min": 25,
                "salary_max": 45,
                "location": "北京",
                "skills": ["Python", "PyTorch", "机器学习", "深度学习"],
                "job_description": "负责机器学习算法研发...",
                "source": "external_collector",
                "source_url": "https://example.com/job/123"
            }
        ],
        "skip_llm_enhance": False
    }
    
    return ApiResponse(
        success=True,
        message="数据导入模板",
        data=template
    )
