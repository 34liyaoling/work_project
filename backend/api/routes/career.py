"""职业路径规划API路由"""

import logging
from fastapi import APIRouter, HTTPException, Query
from backend.schemas.models import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/career", tags=["职业路径"])


@router.post("/plan", response_model=ApiResponse)
async def plan_career_path(current_role: str = "", target_role: str = "",
                           years: int = Query(5, description="目标年限")):
    """职业路径规划 - 基于图谱中的岗位关系和技能依赖"""
    try:
        from core.graph_service import get_graph_service
        graph = get_graph_service()

        jobs = graph.get_all_jobs(status="active")
        job_titles = [j.get("title") or j.get("j.title", "") for j in jobs]

        # 生成多条职业路径
        paths = _generate_career_paths(current_role, target_role, years, job_titles)

        return ApiResponse(data={
            "paths": paths,
            "available_jobs": job_titles,
            "total_jobs": len(job_titles),
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"职业路径规划失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _generate_career_paths(current: str, target: str, years: int, all_jobs: list[str]) -> list[dict]:
    """基于图谱数据和LLM生成职业发展规划"""
    from core.llm_service import get_llm_service
    llm = get_llm_service()

    if not llm.is_ready:
        raise HTTPException(
            status_code=503,
            detail=ApiResponse(success=False, error_message="LLM服务未就绪").model_dump()
        )

    # 构建提示词，让 LLM 基于图谱中的真实岗位数据生成路径
    job_list_text = "\n".join([f"- {title}" for title in all_jobs[:30]])

    prompt = f"""你是一个职业规划专家。请根据以下已有的岗位列表，为用户生成 {years} 年的职业发展路径。

当前角色: {current or '未指定'}
目标角色: {target or '未指定'}
可用岗位列表:
{job_list_text}

请生成 2-3 条不同的职业发展路径（技术专家路线、AI转型路线、管理路线等），每条路径包含：
- name: 路径名称
- description: 路径描述
- type: 路径类型(technical/ai_transition/management)
- milestones: 按年份的里程碑数组，每个包含 year/role/skills/salary_range
- key_technologies: 关键技术栈
- suitable_for: 适合人群

严格以 JSON 数组格式输出，不要添加任何额外说明。"""

    result = llm.chat_completion_json(
        messages=[
            {"role": "system", "content": "你是专业的职业规划顾问，擅长根据技能图谱分析职业发展路径。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
    )

    if result and isinstance(result, list) and len(result) > 0:
        return result

    raise HTTPException(
        status_code=503,
        detail=ApiResponse(success=False, error_message="LLM服务未就绪").model_dump()
    )


@router.get("/roles", response_model=ApiResponse)
async def get_available_roles():
    """获取所有可用角色（用于职业路径起点/终点选择）"""
    from core.graph_service import get_graph_service
    graph = get_graph_service()
    jobs = graph.get_all_jobs(status="active")
    roles = [{"title": j.get("title") or j.get("j.title", ""),
              "domain": j.get("domain") or j.get("j.domain", ""),
              "salary_min": j.get("avg_salary_min") or j.get("j.avg_salary_min", 0),
              "salary_max": j.get("avg_salary_max") or j.get("j.avg_salary_max", 0)}
             for j in jobs]
    return ApiResponse(data={"roles": roles})
