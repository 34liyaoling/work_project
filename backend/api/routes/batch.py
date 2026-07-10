"""批量分析API路由"""

import logging
import tempfile
import os
from fastapi import APIRouter, HTTPException, UploadFile, File
from backend.schemas.models import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/batch", tags=["批量分析"])

# 批量解析结果存储
_batch_results: dict = {}


@router.post("/upload", response_model=ApiResponse)
async def batch_upload_resumes(files: list[UploadFile] = File(...)):
    """批量上传简历文件进行解析"""
    results = []

    for file in files:
        try:
            suffix = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "txt"
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name

            from agents.resume_parser import ResumeParserAgent
            parser = ResumeParserAgent()
            profile = parser.parse_resume(tmp_path)

            from core.credibility_scorer import CredibilityScorer
            cred = CredibilityScorer().get_overall_credibility(profile.skills_with_credibility)

            result = {
                "filename": file.filename,
                "resume_id": profile.resume_hash,
                "name": profile.name,
                "skill_count": len(profile.skills_with_credibility),
                "credibility_score": cred["overall_score"],
                "top_skills": [s.skill_name for s in profile.skills_with_credibility[:8]],
                "domains": list(profile.domain_expertise.keys()) if profile.domain_expertise else [],
                "experience_years": profile.total_experience_years,
            }
            results.append(result)

            # 清理临时文件
            os.unlink(tmp_path)

        except Exception as e:
            results.append({"filename": file.filename, "error": str(e)})
            logger.error(f"批量解析[{file.filename}]失败: {e}")

    batch_id = f"batch_{os.urandom(4).hex()}"
    _batch_results[batch_id] = {
        "results": results,
        "total": len(files),
        "success": sum(1 for r in results if "error" not in r),
        "failed": sum(1 for r in results if "error" in r),
    }

    return ApiResponse(
        message=f"批量解析完成: {sum(1 for r in results if 'error' not in r)}/{len(files)} 成功",
        data={"batch_id": batch_id, **_batch_results[batch_id]}
    )


@router.get("/{batch_id}/result", response_model=ApiResponse)
async def get_batch_result(batch_id: str):
    """获取批量分析结果"""
    result = _batch_results.get(batch_id)
    if not result:
        raise HTTPException(status_code=404, detail="批次不存在")

    # 计算团队技能矩阵
    all_skills = {}
    domain_stats = {}

    for r in result["results"]:
        if "error" in r:
            continue
        name = r.get("name", "未知")
        for skill in r.get("top_skills", []):
            if skill not in all_skills:
                all_skills[skill] = {}
            all_skills[skill][name] = True
        for dom in r.get("domains", []):
            domain_stats[dom] = domain_stats.get(dom, 0) + 1

    return ApiResponse(data={
        **result,
        "skill_matrix": all_skills,
        "domain_coverage": domain_stats,
        "team_skill_count": len(all_skills),
    })


@router.get("/{batch_id}/gap-analysis", response_model=ApiResponse)
async def batch_gap_analysis(batch_id: str, target_job: str = ""):
    """批量差距分析 - 团队整体与目标岗位的技能缺口"""
    result = _batch_results.get(batch_id)
    if not result:
        raise HTTPException(status_code=404, detail="批次不存在")

    # 收集所有人技能
    team_skills = set()
    for r in result["results"]:
        if "error" not in r:
            team_skills.update(r.get("top_skills", []))

    # 获取目标岗位所需技能
    required_skills = []
    if target_job:
        from core.graph_service import get_graph_service
        graph = get_graph_service()
        req = graph.get_job_required_skills(target_job)
        required_skills = [s.get("skill_name", "") for s in req if s.get("relation_type") == "requires"]

    missing = [s for s in required_skills if s not in team_skills]
    covered = [s for s in required_skills if s in team_skills]

    return ApiResponse(data={
        "target_job": target_job,
        "team_size": result["success"],
        "team_skills": sorted(team_skills),
        "required_skills": required_skills,
        "covered_skills": covered,
        "missing_skills": missing,
        "coverage_rate": len(covered) / max(len(required_skills), 1) * 100 if required_skills else 0,
        "recommendations": [
            f"团队缺少「{s}」技能，建议培训或招聘补充" for s in missing[:5]
        ] if missing else ["团队技能覆盖良好！"],
    })
