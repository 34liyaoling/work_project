"""智能匹配Agent"""

import logging
from typing import Any
from .base_agent import BaseKnowledgeAgent
from core.match_engine import HybridMatchEngine
from core.graph_service import get_graph_service
from core.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class MatchingAgent(BaseKnowledgeAgent):
    """智能匹配Agent

    功能：
    1. 混合匹配（图谱+向量+LLM）
    2. 匹配解释生成
    3. 排序与筛选
    4. What-If模拟匹配
    """

    agent_name = "matching_agent"
    agent_description = "智能匹配专家 - 多维度的精准人岗匹配引擎"

    def __init__(self):
        super().__init__()
        self.engine = HybridMatchEngine()
        self.graph = get_graph_service()
        self.llm = get_llm_service()
        self.match_history: list[dict] = []

    def _setup_tools(self):
        pass

    def find_matches(self, resume_profile: dict, top_n: int = 10) -> dict:
        """查找最佳匹配岗位"""
        from core.data_lifecycle import DataLifecycleManager

        jobs = self.graph.get_all_jobs(status="active")
        if not jobs:
            jobs = self.graph.get_all_jobs(status="all")
        if not jobs:
            return {"matches": [], "message": "暂无岗位数据"}

        lifecycle = DataLifecycleManager()

        # 构建岗位需求格式（含数据新鲜度）
        job_requirements = []
        for job in jobs:
            title = job.get("title", "")
            req_skills = self.graph.get_job_required_skills(title)
            required = [s["skill_name"] for s in req_skills if s.get("relation_type") == "requires"]
            optional = [s["skill_name"] for s in req_skills if s.get("relation_type") == "prefers"]

            # 计算数据新鲜度（从图库中取 last_updated）
            last_updated = job.get("last_updated")
            lu_str = str(last_updated)[:19] if last_updated else None
            freshness = lifecycle.compute_freshness(lu_str)
            lifecycle_status = lifecycle.determine_lifecycle(lu_str)

            # 计算数据年龄（天）
            data_age_days = None
            if lu_str:
                try:
                    from datetime import datetime
                    lu_dt = datetime.fromisoformat(lu_str)
                    data_age_days = (datetime.now() - lu_dt).days
                except Exception:
                    pass

            job_req = {
                "title": title,
                "required_skills": required,
                "optional_skills": optional,
                "domain": job.get("domain", ""),
                "salary_range": (job.get("avg_salary_min", 0), job.get("avg_salary_max", 0)),
                "data_freshness": freshness,
                "data_age_days": data_age_days,
                "lifecycle_status": lifecycle_status,
            }
            job_requirements.append(job_req)

        # 批量匹配（含新鲜度调整）
        results = self.engine.batch_calculate(resume_profile, job_requirements)
        top_matches = results[:top_n]

        match_details = []
        for m in top_matches:
            match_details.append({
                "job_title": m.job_title,
                "match_score": m.score,
                "breakdown": m.breakdown,
                "matched_skills": m.matched_skills,
                "missing_critical": m.missing_critical,
                "missing_optional": m.missing_optional,
                "explanation": m.explanation,
            })

        output = {
            "matches": match_details,
            "total_jobs_scanned": len(jobs),
            "top_match": match_details[0] if match_details else None,
            "resume_profile_summary": {
                "skill_count": len(resume_profile.get("skills", [])),
                "has_implicit": len(resume_profile.get("implicit_skills", [])) > 0,
            },
        }

        self.match_history.append(output)
        return output

    def simulate_what_if(self, resume_profile: dict, added_skills: list[str]) -> dict:
        """What-If模拟：假设学习了新技能后的匹配变化"""
        original = self.find_matches(resume_profile, top_n=5)

        # 创建增强画像
        enhanced = {
            **resume_profile,
            "skills": resume_profile.get("skills", []) + added_skills,
        }
        enhanced_result = self.find_matches(enhanced, top_n=5)

        # 对比差异
        comparison = self._compare_match_results(original, enhanced_result, added_skills)

        return {
            "original_top3": original.get("matches", [])[:3],
            "enhanced_top3": enhanced_result.get("matches", [])[:3],
            "comparison": comparison,
            "added_skills": added_skills,
            "recommendation": self._gen_whatif_recommendation(comparison, added_skills),
        }

    def _compare_match_results(self, original: dict, enhanced: dict, added_skills: list[str]) -> dict:
        """对比前后匹配结果"""
        orig_titles = set(m["job_title"] for m in original.get("matches", []))
        enh_titles = set(m["job_title"] for m in enhanced.get("matches", []))

        new_unlocked = enh_titles - orig_titles
        improved = []

        for enh_m in enhanced.get("matches", []):
            for orig_m in original.get("matches", []):
                if enh_m["job_title"] == orig_m["job_title"]:
                    delta = enh_m["match_score"] - orig_m["match_score"]
                    if delta > 0.03:
                        improved.append({
                            "job": enh_m["job_title"],
                            "before": round(orig_m["match_score"], 3),
                            "after": round(enh_m["match_score"], 3),
                            "delta": round(delta, 3),
                        })

        return {
            "new_unlocked_jobs": list(new_unlocked),
            "improved_jobs": improved,
            "score_change_avg": (
                sum(m["match_score"] for m in enhanced.get("matches", [])) / max(len(enhanced.get("matches", [])), 1)
                - sum(m["match_score"] for m in original.get("matches", [])) / max(len(original.get("matches", [])), 1)
            ) if original.get("matches") and enhanced.get("matches") else 0,
        }

    def _gen_whatif_recommendation(self, comparison: dict, added_skills: list[str]) -> str:
        """生成What-If建议"""
        new_count = len(comparison.get("new_unlocked_jobs", []))
        improved_count = len(comparison.get("improved_jobs", []))
        score_delta = comparison.get("score_change_avg", 0)

        parts = [f"学习了{', '.join(added_skills)}后："]
        if new_count > 0:
            parts.append(f"- 可解锁{new_count}个新岗位: {', '.join(comparison['new_unlocked_jobs'][:5])}")
        if improved_count > 0:
            parts.append(f"- {improved_count}个岗位匹配度提升")
        if score_delta > 0:
            parts.append(f"- 平均匹配度提升{score_delta:+.1%}")

        return "\n".join(parts)

    def _form_hypothesis(self, task_input: Any, perception: dict) -> dict:
        return {"strategy": "hybrid_matching_engine"}

    def _act(self, hypothesis: Any, task_input: Any, **kwargs) -> Any:
        resume = kwargs.get("resume_profile")
        if resume:
            top_n = kwargs.get("top_n", 10)
            return self.find_matches(resume, top_n)
        return {"error": "需要提供resume_profile参数"}
