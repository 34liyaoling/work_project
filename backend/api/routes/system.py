"""系统健康检查与管理API路由"""

import logging
import time
from datetime import datetime
from fastapi import APIRouter, HTTPException
from backend.schemas.models import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system", tags=["系统管理"])


@router.get("/health", response_model=ApiResponse)
async def health_check():
    """全面健康检查 - 检查所有组件状态"""
    checks = []

    # 1. Neo4j检查
    try:
        from core.graph_service import get_graph_service
        graph = get_graph_service()
        start = time.time()
        stats = graph.get_graph_stats()
        latency = round((time.time() - start) * 1000)
        total_nodes = stats.get("total_nodes", 0)
        status = "通过" if total_nodes > 0 else "告警"
        detail = f"连接正常，节点数={total_nodes}，延迟={latency}ms"
    except Exception as e:
        status = "异常"
        detail = str(e)
    checks.append({"item": "Neo4j 图数据库", "status": status, "detail": detail})

    # 2. ChromaDB检查
    try:
        from core.vector_service import get_vector_service
        vector = get_vector_service()
        if vector.is_connected:
            coll_stats = vector.get_collection_stats("skills")
            status = "通过"
            detail = f"连接正常，向量数={coll_stats.get('count', 0)}"
        else:
            status = "告警"
            detail = "未连接（向量检索功能受限）"
    except Exception as e:
        status = "异常"
        detail = str(e)
    checks.append({"item": "ChromaDB 向量数据库", "status": status, "detail": detail})

    # 3. LLM检查
    try:
        from core.llm_service import get_llm_service
        llm = get_llm_service()
        if llm.is_ready:
            ok, msg = llm.test_connection()
            status = "通过" if ok else "异常"
            detail = msg
        else:
            status = "告警"
            detail = "客户端未初始化（请配置SPARK_API_KEY）"
    except Exception as e:
        status = "异常"
        detail = str(e)
    checks.append({"item": "LLM 大模型服务", "status": status, "detail": detail})

    # 4. 图谱完整性检查
    try:
        from core.graph_service import get_graph_service
        graph = get_graph_service()
        stats = graph.get_graph_stats()
        total = stats.get("total_nodes", 0)
        relations = stats.get("total_relations", 0)
        orphan_ratio = 0
        if total > 0:
            # 孤立节点检测
            try:
                orphans = graph.execute_query(
                    "MATCH (n) WHERE size((n)--()) = 0 RETURN count(n) AS cnt"
                )
                orphan_count = orphans[0]["cnt"] if orphans else 0
                orphan_ratio = orphan_count / total
            except:
                orphan_ratio = 0

        if orphan_ratio > 0.3:
            status = "告警"
            detail = f"孤立节点比例较高({orphan_ratio:.1%})"
        elif total == 0:
            status = "告警"
            detail = "图谱为空（需执行初始化或构建）"
        else:
            status = "通过"
            detail = f"节点={total}, 关系={relations}, 完整性良好"
    except Exception as e:
        status = "异常"
        detail = str(e)
    checks.append({"item": "知识图谱完整性", "status": status, "detail": detail})

    # 5. 数据一致性检查
    try:
        from core.graph_service import get_graph_service
        graph = get_graph_service()
        jobs = graph.get_all_jobs("all")
        skills = graph.get_all_skills(limit=500)
        has_job_without_skills = 0
        for job in jobs:
            title = job.get("title") or job.get("j.title", "")
            req = graph.get_job_required_skills(title)
            if not req:
                has_job_without_skills += 1

        if has_job_without_skills > len(jobs) * 0.5 and len(jobs) > 0:
            status = "告警"
            detail = f"{has_job_without_skills}/{len(jobs)} 个岗位无技能关联"
        else:
            status = "通过"
            detail = f"岗位={len(jobs)}, 技能={len(skills)}, 一致性正常"
    except Exception as e:
        status = "异常"
        detail = str(e)
    checks.append({"item": "数据一致性", "status": status, "detail": detail})

    # 总体评估
    passed = sum(1 for c in checks if c["status"] == "通过")
    warned = sum(1 for c in checks if c["status"] == "告警")
    failed = sum(1 for c in checks if c["status"] == "异常")

    overall = "健康" if failed == 0 and warned <= 1 else "警告" if failed == 0 else "异常"

    return ApiResponse(data={
        "overall_status": overall,
        "checked_at": datetime.now().isoformat(),
        "summary": {"passed": passed, "warned": warned, "failed": failed, "total": len(checks)},
        "checks": checks,
    })


@router.get("/audit-queue", response_model=ApiResponse)
async def get_audit_queue():
    """获取审核队列（幻觉防控L4层）"""
    try:
        from core.hallucination_guard import HallucinationGuard
        from core.graph_service import get_graph_service
        guard = HallucinationGuard(get_graph_service())
        status = guard.get_review_queue_status()
        items = guard.get_pending_items(limit=20)
        return ApiResponse(data={"queue_status": status, "items": items})
    except Exception as e:
        # 返回空队列而非报错
        return ApiResponse(data={
            "queue_status": {"pending_count": 0, "approved_count": 0, "rejected_count": 0},
            "items": [],
            "note": f"审核队列暂无数据或未初始化: {str(e)[:100]}"
        })


@router.post("/audit/{item_id}", response_model=ApiResponse)
async def audit_action(item_id: str, action: str = "approve", note: str = ""):
    """审核操作 - 通过或拒绝"""
    try:
        from core.hallucination_guard import HallucinationGuard
        from core.graph_service import get_graph_service
        guard = HallucinationGuard(get_graph_service())

        if action == "approve":
            guard.approve(item_id)
            message = f"已通过审核项 {item_id}"
        elif action == "reject":
            guard.reject(item_id, reason=note)
            message = f"已拒绝审核项 {item_id}"
        else:
            raise HTTPException(status_code=400, detail=f"不支持的操作: {action}")

        return ApiResponse(message=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
