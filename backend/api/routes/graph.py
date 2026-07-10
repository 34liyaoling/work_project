"""知识图谱API路由"""

import json
import logging
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from backend.schemas.models import ApiResponse, GraphStatsResponse, GraphQueryRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/graph", tags=["知识图谱"])


@router.get("/stats", response_model=ApiResponse)
async def get_graph_statistics():
    """获取图谱统计信息"""
    # 保护性导入（确保 Optional 可用）
    from typing import Optional

    try:
        from core.graph_service import get_graph_service
        graph = get_graph_service()

        if not graph.is_connected:
            graph.connect()
            graph.initialize_schema()
            graph.seed_initial_domains()

        stats = graph.get_graph_stats()

        # 额外统计
        all_jobs = graph.get_all_jobs("all")
        all_skills = graph.get_all_skills(limit=50)
        all_domains = []

        # 获取领域列表
        domain_nodes = graph.execute_query("MATCH (d:Domain) RETURN d.name as name, d.description as desc")
        all_domains = [{"name": d["name"], "description": d.get("desc", "")} for d in domain_nodes]

        return ApiResponse(
            data={
                "stats": stats,
                "job_count": len(all_jobs),
                "skill_sample": all_skills[:20],
                "domains": all_domains,
            }
        )
    except Exception as e:
        logger.error(f"图谱查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", response_model=ApiResponse)
async def get_jobs(status: str = Query("all", description="岗位状态")):
    """获取所有岗位"""
    from core.graph_service import get_graph_service
    graph = get_graph_service()

    jobs = graph.get_all_jobs(status=status)
    return ApiResponse(data={"jobs": jobs, "count": len(jobs)})


@router.get("/skills", response_model=ApiResponse)
async def get_skills(domain: str = Query(None, description="按领域过滤"),
                     limit: int = Query(100)):
    """获取技能列表"""
    from core.graph_service import get_graph_service
    graph = get_graph_service()

    skills = graph.get_all_skills(domain=domain, limit=limit)
    return ApiResponse(data={"skills": skills, "count": len(skills)})


@router.get("/job/{job_title}/skills", response_model=ApiResponse)
async def get_job_skills(job_title: str):
    """获取岗位所需技能"""
    from core.graph_service import get_graph_service
    graph = get_graph_service()

    skills = graph.get_job_required_skills(job_title)
    return ApiResponse(data={
        "job_title": job_title,
        "required_skills": [s for s in skills if s.get("relation_type") == "requires"],
        "optional_skills": [s for s in skills if s.get("relation_type") == "prefers"],
    })


@router.get("/search", response_model=ApiResponse)
async def search_graph(q: str = Query(..., description="搜索关键词")):
    """搜索知识图谱中的技能和岗位"""
    from core.graph_service import get_graph_service
    graph = get_graph_service()

    try:
        cypher = """
        CALL db.index.fulltext.queryNodes("skill_fulltext", $query) YIELD node as skill
        OPTIONAL MATCH (skill)<-[:requires]-(j:Job)
        RETURN skill.name as name, labels(skill) as type,
               collect(DISTINCT j.title) as related_jobs
        LIMIT 20
        """
        results = graph.execute_query(cypher, {"query": q})

        # 如果全文索引不存在，回退到模糊匹配
        if not results:
            cypher = """
            MATCH (n)
            WHERE n.name CONTAINS $query OR n.title CONTAINS $query
            RETURN coalesce(n.name, n.title) as name,
                   labels(n)[0] as type,
                   [] as related_jobs
            LIMIT 20
            """
            results = graph.execute_query(cypher, {"query": q})

        return ApiResponse(data={"query": q, "results": results, "count": len(results)})
    except Exception as e:
        logger.warning(f"搜索查询异常: {e}")
        cypher = """
        MATCH (n) WHERE n.name CONTAINS $query OR n.title CONTAINS $query
        RETURN coalesce(n.name, n.title) as name, labels(n)[0] as type, [] as related_jobs
        LIMIT 10
        """
        results = graph.execute_query(cypher, {"query": q})
        return ApiResponse(data={"query": q, "results": results, "count": len(results)})


@router.post("/initialize", response_model=ApiResponse)
async def initialize_graph():
    """初始化图谱（创建Schema，不写入种子数据）"""
    try:
        from core.graph_service import get_graph_service
        graph = get_graph_service()
        if not graph.is_connected:
            graph.connect()
        graph.initialize_schema()
        return ApiResponse(data={"message": "图谱Schema初始化成功", "nodes_created": 0})
    except Exception as e:
        logger.error(f"图谱初始化失败: {e}")
        return ApiResponse(success=False, message=f"图谱初始化失败: {e}")


@router.post("/build", response_model=ApiResponse)
async def build_from_collection():
    """从已采集的数据构建图谱"""
    try:
        from agents.data_collector import DataCollectorAgent
        from agents.graph_builder import GraphBuilderAgent

        # 先采集数据
        collector = DataCollectorAgent()
        collection_result = collector.collect_all_sources()

        # 构建图谱
        builder = GraphBuilderAgent()
        processed = collection_result["processed_data"]
        build_data = [{
            "job_title": j.job_title,
            "company_name": j.company_name or "",
            "skills": j.skills or [],
            "salary_min": j.salary_min,
            "salary_max": j.salary_max,
            "location": j.location or "",
            "source": j.source.value if hasattr(j.source, 'value') else str(j.source),
        } for j in processed] if processed else []
        build_result = builder.build_from_data(build_data)

        return ApiResponse(
            message=f"图谱构建完成，新增{build_result['skills_added']}个技能节点，"
                    f"更新{build_result['jobs_updated']}个岗位",
            data={**collection_result, **build_result},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect-from-web")
async def collect_from_web_api():
    """从互联网采集真实岗位数据并写入图谱

    完整流程：
    1. 从搜索引擎搜索真实招聘信息
    2. 用LLM为搜索结果推断技能要求
    3. 写入Neo4j知识图谱

    Returns:
        JSONResponse: 包含采集结果、LLM增强数量和图谱构建结果
    """
    try:
        logger.info("收到从网络采集数据的请求")

        from agents.data_collector import DataCollectorAgent
        from agents.graph_builder import GraphBuilderAgent

        # Step 1: 从搜索引擎搜索招聘信息
        collector = DataCollectorAgent()
        search_result = collector.collect_all_sources()
        raw_jobs = search_result.get("processed_data", [])

        if not raw_jobs:
            return JSONResponse(
                status_code=404,
                content={
                    "code": 404,
                    "message": "未从网络搜索到任何招聘数据，请确保网络连接正常后重试",
                    "data": {"collected": 0}
                }
            )

        # Step 2: 用LLM为搜索结果推断技能要求
        enhanced_jobs = collector.enhance_search_results_with_llm(raw_jobs)

        # Step 3: 写入Neo4j图谱
        builder = GraphBuilderAgent()
        build_data = [{
            "job_title": j.job_title,
            "company_name": j.company_name or "",
            "skills": j.skills or [],
            "salary_min": j.salary_min,
            "salary_max": j.salary_max,
            "location": j.location or "",
            "source": j.source.value if hasattr(j.source, 'value') else str(j.source),
        } for j in enhanced_jobs]

        build_result = builder.build_from_data(build_data)

        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "message": f"从网络采集了 {len(raw_jobs)} 条招聘数据，"
                          f"LLM增强了 {sum(1 for j in enhanced_jobs if j.skills)} 条技能信息，"
                          f"写入图谱 {build_result.get('jobs_updated', 0)} 个岗位",
                "data": {
                    "collected": len(raw_jobs),
                    "enhanced": sum(1 for j in enhanced_jobs if j.skills),
                    "graph": build_result,
                    "sources": "Bing搜索引擎",
                }
            }
        )

    except Exception as e:
        logger.error(f"从网络采集数据失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"从网络采集数据时发生错误: {str(e)}"
        )
