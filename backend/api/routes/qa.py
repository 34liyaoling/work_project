"""智能问答API路由 - 基于知识图谱的 GraphRAG 问答

问答流程：
1. 从用户问题中识别图谱实体（技能名/岗位名/领域名）
2. 根据实体查询 Neo4j 子图（岗位-技能关系、技能相似关系、技能归属领域等）
3. 把检索到的真实子图数据作为上下文，让 LLM 生成回答
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from backend.schemas.models import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/qa", tags=["智能问答"])


def _retrieve_graph_context(question: str, graph) -> str:
    """从知识图谱中检索与问题相关的上下文

    通过实体匹配 + 子图查询，而非简单塞名单。
    """
    context_parts = []

    # 1. 获取图谱所有节点名，用于实体识别
    all_skills = graph.get_all_skills(limit=500)
    skill_names = [s.get("name") or s.get("s.name", "") for s in all_skills if s.get("name") or s.get("s.name")]

    all_jobs = graph.get_all_jobs(status="all")
    job_titles = [j.get("title") or j.get("j.title", "") for j in all_jobs if j.get("title") or j.get("j.title", "")]

    # 2. 从问题中匹配实体（大小写不敏感）
    question_lower = question.lower()
    matched_skills = [s for s in skill_names if s and s.lower() in question_lower]
    matched_jobs = [j for j in job_titles if j and j.lower() in question_lower]

    # 去重，限制数量
    matched_skills = list(dict.fromkeys(matched_skills))[:10]
    matched_jobs = list(dict.fromkeys(matched_jobs))[:10]

    # 3. 根据匹配到的岗位，查询其所需技能
    if matched_jobs:
        for job_title in matched_jobs[:5]:
            job_skills = graph.get_job_required_skills(job_title, fuzzy=False)
            if job_skills:
                requires = [s["skill_name"] for s in job_skills if s.get("relation_type") == "requires"]
                prefers = [s["skill_name"] for s in job_skills if s.get("relation_type") == "prefers"]
                skill_info = f"岗位「{job_title}」"
                if requires:
                    skill_info += f" 必备技能: {', '.join(requires)}"
                if prefers:
                    skill_info += f" 加分技能: {', '.join(prefers)}"
                context_parts.append(skill_info)

    # 4. 根据匹配到的技能，查询相关岗位和相似技能
    if matched_skills:
        for skill_name in matched_skills[:5]:
            # 查找哪些岗位需要这个技能
            cypher_jobs = """
            MATCH (j:Job)-[r:requires]->(s:Skill {name: $skill})
            RETURN j.title AS job_title, j.avg_salary_min AS salary_min, j.avg_salary_max AS salary_max
            LIMIT 10
            """
            try:
                jobs_for_skill = graph.execute_query(cypher_jobs, {"skill": skill_name})
                if jobs_for_skill:
                    job_list = [f"{j['job_title']}" for j in jobs_for_skill[:8]]
                    salary_info = ""
                    salaries = [j.get("salary_max", 0) for j in jobs_for_skill if j.get("salary_max")]
                    if salaries:
                        salary_info = f"（相关岗位薪资上限约{max(salaries)/1000:.0f}K）"
                    context_parts.append(f"技能「{skill_name}」被{len(jobs_for_skill)}个岗位要求{salary_info}：{', '.join(job_list)}")
            except Exception:
                pass

            # 查找相似技能
            similar = graph.find_similar_skills(skill_name, limit=5)
            if similar:
                similar_names = [s.get("similar.name", "") for s in similar if s.get("similar.name")]
                if similar_names:
                    context_parts.append(f"技能「{skill_name}」的相似技能：{', '.join(similar_names)}")

    # 5. 如果没匹配到具体实体，提供图谱概览统计
    if not matched_skills and not matched_jobs:
        stats = graph.get_graph_stats()
        # 取热门技能（按 trend_score）
        top_skills = sorted(all_skills, key=lambda x: x.get("trend_score") or x.get("s.trend_score") or 0, reverse=True)[:10]
        top_names = [s.get("name") or s.get("s.name", "") for s in top_skills if s.get("name") or s.get("s.name")]
        context_parts.append(
            f"知识图谱概览：共{stats.get('total_nodes', 0)}个节点"
            f"（{stats.get('skill_nodes', 0)}个技能、{stats.get('job_nodes', 0)}个岗位）"
            f"，{stats.get('total_relations', 0)}条关系。\n"
            f"热门技能：{', '.join(top_names)}"
        )

    return "\n".join(context_parts) if context_parts else "（未检索到相关图谱数据）"


@router.post("/ask", response_model=ApiResponse)
async def ask_question(question: str = Query(..., description="用户问题")):
    """智能问答 - 基于图谱子图检索 + LLM 生成回答"""
    # 空问题直接拦截，避免浪费 LLM 调用
    if not question or not question.strip():
        return ApiResponse(
            success=False,
            error_message="问题不能为空，请输入具体问题",
            data={"answer": "请输入您想了解的问题，例如「Python开发岗位需要哪些技能」"}
        )
    try:
        from core.llm_service import get_llm_service
        from core.graph_service import get_graph_service

        llm = get_llm_service()
        graph = get_graph_service()

        if not llm.is_ready:
            raise HTTPException(
                status_code=503,
                detail=ApiResponse(success=False, error_message="LLM服务未就绪").model_dump()
            )

        # 1. 从图谱检索与问题相关的子图数据
        graph_context = ""
        try:
            graph_context = _retrieve_graph_context(question, graph)
            logger.info(f"[QA] 检索到图谱上下文: {len(graph_context)}字")
        except Exception as e:
            logger.warning(f"[QA] 图谱检索失败: {e}")
            graph_context = "（图谱检索失败）"

        # 2. 构建Prompt
        system_prompt = """你是新一代信息技术全景图谱系统的智能问答助手。
你的回答必须基于以下知识图谱检索到的真实数据。请用中文回答，专业、简洁、有深度。

规则：
1. 优先使用图谱上下文中的数据回答，不要编造图谱中不存在的技能或岗位
2. 如果图谱数据足以回答，给出具体数据支撑
3. 如果图谱数据不足，诚实说明并补充通用知识，但需标注哪些来自图谱、哪些是通用知识"""

        user_message = f"【知识图谱检索结果】\n{graph_context}\n\n【用户问题】\n{question}"

        # 3. 调用LLM
        answer = llm.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=1500,
        )
        if not answer:
            raise HTTPException(
                status_code=503,
                detail=ApiResponse(success=False, error_message="LLM服务未就绪").model_dump()
            )

        return ApiResponse(
            data={"answer": answer, "sources": ["knowledge_graph", "llm"]}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"问答失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))



