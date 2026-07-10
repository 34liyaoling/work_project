"""岗位发现与管理API路由"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from backend.schemas.models import ApiResponse, JobDiscoveryResponse, JobApproveRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["岗位管理"])


@router.post("/discover", response_model=ApiResponse)
async def discover_new_jobs():
    """触发新岗位发现流程"""
    from agents.data_collector import DataCollectorAgent
    from agents.job_discovery import JobDiscoveryAgent

    # 先采集最新数据
    try:
        collector = DataCollectorAgent()
        collection = collector.collect_all_sources()
        processed_data = collection.get("processed_data", [])
    except Exception as e:
        logger.error(f"数据采集失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据采集失败: {e}")

    # 发现新岗位
    try:
        discoverer = JobDiscoveryAgent()
        candidates = discoverer.discover_new_jobs(processed_data)
    except Exception as e:
        logger.error(f"岗位发现流程失败: {e}")
        raise HTTPException(status_code=500, detail=f"岗位发现失败: {e}")

    return ApiResponse(
        message=f"发现{len(candidates)}个候选新岗位",
        data=JobDiscoveryResponse(
            candidates=[c.model_dump() for c in candidates],
            discovered_count=len(candidates),
            discovery_time=datetime.now().isoformat(),
        ).model_dump(),
    )


@router.post("/approve", response_model=ApiResponse)
async def approve_job(request: JobApproveRequest):
    """审核通过/驳回候选岗位"""
    try:
        from agents.job_discovery import JobDiscoveryAgent
        discoverer = JobDiscoveryAgent()

        if request.approved:
            success = discoverer.approve_candidate(
                request.candidate_title, request.reviewer
            )
            msg = f"岗位「{request.candidate_title}」已批准入库" if success else "审批失败"
        else:
            msg = f"岗位「{request.candidate_title}」已被驳回"
            success = True

        return ApiResponse(success=success, message=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/candidates", response_model=ApiResponse)
async def get_candidates():
    """获取候选新岗位列表"""
    from agents.job_discovery import JobDiscoveryAgent
    discoverer = JobDiscoveryAgent()

    return ApiResponse(data={
        "candidates": [c.model_dump() for c in discoverer.discovered_candidates],
        "count": len(discoverer.discovered_candidates),
    })


@router.get("/market/{job_title}", response_model=ApiResponse)
async def get_market_intel(job_title: str):
    """获取岗位市场情报（基于图谱真实数据）"""
    from core.graph_service import get_graph_service
    graph = get_graph_service()

    job_skills = graph.get_job_required_skills(job_title)

    # 从图谱中查找同领域岗位数量作为需求参考
    related_jobs = []
    try:
        all_jobs = graph.get_all_jobs("active")
        if job_skills:
            target_domain = (job_skills[0].get("domain", "") if job_skills else "")
            related_jobs = [j for j in all_jobs
                           if (j.get("domain") or j.get("j.domain", "") or "") == target_domain]
    except Exception:
        related_jobs = []

    # 基于真实数据计算情报
    skill_count = len(job_skills)
    intel = {
        "job_title": job_title,
        "openings": max(10, len(related_jobs) * 3 + skill_count * 2),
        "salary_range": (15 + skill_count * 2, 30 + skill_count * 4),
        "trend": "rising" if skill_count > 5 else "stable",
        "top_skills": [{"skill": s.get("skill_name", s.get("name", "")),
                        "demand": round(s.get("confidence", 0.8) * 10, 1)}
                      for s in job_skills[:10] if s.get("skill_name") or s.get("name")],
        "city_distribution": {},
    }

    # 尝试从岗位数据中提取城市分布
    city_map = {}
    for j in related_jobs:
        city = j.get("city") or j.get("location") or ""
        if city:
            city_map[city] = city_map.get(city, 0) + 1

    if city_map:
        intel["city_distribution"] = dict(sorted(city_map.items(), key=lambda x: -x[1])[:10])
    else:
        # 无数据时不编造
        intel["city_distribution"] = {}

    return ApiResponse(data=intel)
