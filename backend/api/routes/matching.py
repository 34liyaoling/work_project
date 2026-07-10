"""智能匹配与差距分析API路由"""

import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from backend.schemas.models import (
    ApiResponse, MatchRequest, MatchResponse, MatchResultItem,
    GapAnalysisRequest, GapAnalysisResponse,
    WhatIfRequest, WhatIfResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/matching", tags=["匹配分析"])


@router.post("/match", response_model=ApiResponse)
async def match_jobs(request: MatchRequest):
    """执行人岗匹配"""
    try:
        from agents.matching_agent import MatchingAgent
        from backend.storage import get_db
        from models.resume_model import ResumeProfile

        profile_data = get_db().get_resume(request.resume_id)
        if not profile_data:
            return JSONResponse(
                status_code=404,
                content=ApiResponse(success=False, message="简历未找到").model_dump(),
            )

        profile = ResumeProfile(**profile_data)

        resume_dict = {
            "skills": profile.skills_explicit + profile.skills_implicit,
            "implicit_skills": profile.skills_implicit,
            "embedding": profile.embedding_vector,
            "skills_with_credibility": [s.model_dump() for s in profile.skills_with_credibility],
        }

        matcher = MatchingAgent()
        result = matcher.find_matches(resume_dict, top_n=request.top_n)

        match_items = [
            MatchResultItem(**m) for m in result.get("matches", [])
        ]

        # 质量守护：验证匹配结果质量
        quality_check = None
        try:
            from agents.quality_guardian import QualityGuardianAgent
            guardian = QualityGuardianAgent()
            quality_check = guardian.verify_output({
                "matches": match_items,
                "total_scanned": result.get("total_jobs_scanned", 0),
            })
            if quality_check.get("verdict") == "rejected":
                logger.warning(f"匹配结果质量被拒绝: {quality_check}")
        except Exception as e:
            logger.warning(f"质量守护检查失败: {e}")

        return ApiResponse(
            data=MatchResponse(
                matches=match_items,
                total_scanned=result.get("total_jobs_scanned", 0),
                best_match=match_items[0] if match_items else None,
            ).model_dump() | ({"quality_check": quality_check} if quality_check else {}),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"匹配失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gap", response_model=ApiResponse)
async def analyze_gap(request: GapAnalysisRequest):
    """差距分析"""
    try:
        from backend.storage import get_db
        from models.resume_model import ResumeProfile
        from agents.gap_analyzer import GapAnalyzerAgent

        profile_data = get_db().get_resume(request.resume_id)
        if not profile_data:
            return JSONResponse(
                status_code=404,
                content=ApiResponse(success=False, message="简历未找到").model_dump(),
            )

        profile = ResumeProfile(**profile_data)

        resume_dict = {
            "skills": profile.skills_explicit + profile.skills_implicit,
            "implicit_skills": profile.skills_implicit,
        }

        analyzer = GapAnalyzerAgent()

        if request.target_job:
            result = analyzer.analyze_gaps(resume_dict, request.target_job)
        else:
            result = analyzer.full_gap_analysis(resume_dict)

        return ApiResponse(data=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"差距分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/whatif", response_model=ApiResponse)
async def what_if_analysis(request: WhatIfRequest):
    """What-If 假设性分析"""
    try:
        from backend.storage import get_db
        from models.resume_model import ResumeProfile
        from agents.matching_agent import MatchingAgent

        profile_data = get_db().get_resume(request.resume_id)
        if not profile_data:
            return JSONResponse(
                status_code=404,
                content=ApiResponse(success=False, message="简历未找到").model_dump(),
            )

        profile = ResumeProfile(**profile_data)

        resume_dict = {
            "skills": profile.skills_explicit + profile.skills_implicit,
            "implicit_skills": profile.skills_implicit,
        }

        matcher = MatchingAgent()
        result = matcher.simulate_what_if(resume_dict, request.added_skills)

        return ApiResponse(data=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"What-If分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
