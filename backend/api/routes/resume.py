"""简历解析API路由"""

import logging
import tempfile
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from backend.schemas.models import (ApiResponse, ResumeUploadResponse,
                                     ResumeProfileResponse)
from backend.storage import get_db
from models.resume_model import ResumeProfile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/resume", tags=["简历解析"])


@router.post("/upload", response_model=ApiResponse)
async def upload_resume(file: UploadFile = File(...)):
    """上传并解析简历文件"""
    try:
        # 保存上传的文件
        suffix = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # 解析简历
        from agents.resume_parser import ResumeParserAgent
        parser = ResumeParserAgent()
        profile = parser.parse_resume(tmp_path)

        # 持久化存储
        get_db().save_resume(profile.resume_hash, profile.model_dump())

        from core.credibility_scorer import CredibilityScorer
        cred_overall = CredibilityScorer().get_overall_credibility(profile.skills_with_credibility)

        return ApiResponse(
            message="简历解析完成",
            data=ResumeUploadResponse(
                resume_id=profile.resume_hash,
                name=profile.name,
                skill_count=len(profile.skills_with_credibility),
                credibility_score=cred_overall["overall_score"],
                technical_level=profile.overall_technical_level,
                parsing_time_ms=0,
            ).model_dump(),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="文件不存在或无法读取")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"简历解析失败: {e}")
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


@router.post("/upload-text", response_model=ApiResponse)
async def upload_resume_text(content: str = Form(...)):
    """直接提交简历文本进行解析"""
    try:
        import tempfile
        import os

        # 写入临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # 解析简历
        from agents.resume_parser import ResumeParserAgent
        parser = ResumeParserAgent()
        profile = parser.parse_resume(tmp_path)

        # 持久化存储
        get_db().save_resume(profile.resume_hash, profile.model_dump())

        from core.credibility_scorer import CredibilityScorer
        cred_overall = CredibilityScorer().get_overall_credibility(profile.skills_with_credibility)

        # 清理临时文件
        os.unlink(tmp_path)

        return ApiResponse(
            message="简历解析完成",
            data=ResumeUploadResponse(
                resume_id=profile.resume_hash,
                name=profile.name,
                skill_count=len(profile.skills_with_credibility),
                credibility_score=cred_overall["overall_score"],
                technical_level=profile.overall_technical_level,
                parsing_time_ms=0,
            ).model_dump(),
        )
    except Exception as e:
        logger.error(f"简历文本解析失败: {e}")
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


@router.get("/{resume_id}/profile", response_model=ApiResponse)
async def get_resume_profile(resume_id: str):
    """获取已解析的简历画像"""
    profile_data = get_db().get_resume(resume_id)
    if not profile_data:
        raise HTTPException(status_code=404, detail="简历未找到，请先上传")

    profile = ResumeProfile(**profile_data)

    return ApiResponse(data=ResumeProfileResponse(
        name=profile.name,
        skills_explicit=profile.skills_explicit,
        skills_implicit=profile.skills_implicit,
        skills_with_credibility=[s.model_dump() for s in profile.skills_with_credibility],
        projects=[p.model_dump() for p in profile.projects],
        experience_years=profile.total_experience_years,
        technical_level=profile.overall_technical_level,
        embedding_available=profile.embedding_vector is not None,
    ).model_dump())
