"""混合匹配引擎 - 图谱推理 + 向量检索 + LLM排序"""

import logging
from dataclasses import dataclass
from typing import Optional
from core.llm_service import get_llm_service
from core.graph_service import get_graph_service
from core.vector_service import get_vector_service

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """匹配结果"""
    score: float
    job_title: str
    breakdown: dict
    matched_skills: list[str]
    missing_critical: list[str]
    missing_optional: list[str]
    explanation: str = ""


class HybridMatchEngine:
    """混合匹配引擎

    最终得分 = α × 技能匹配分 + β × 图谱路径分 + γ × 向量相似分 + δ × 趋势加分 + ε × 可信度修正

    默认权重: α=0.35, β=0.20, γ=0.25, δ=0.10, ε=0.10
    """

    DEFAULT_WEIGHTS = {
        "skill": 0.35,       # 技能匹配分
        "graph": 0.20,       # 图谱路径分
        "vector": 0.25,      # 向量相似分
        "trend": 0.10,       # 趋势加分
        "credibility": 0.10, # 可信度修正
    }

    def __init__(self, custom_weights: Optional[dict] = None):
        self.weights = custom_weights or self.DEFAULT_WEIGHTS.copy()
        self.llm = get_llm_service()
        self.graph = get_graph_service()
        self.vector = get_vector_service()

    def calculate_match(self, resume_profile: dict, job_requirement: dict) -> MatchResult:
        """计算简历与岗位的匹配度

        Args:
            resume_profile: 简历画像 {
                "skills": list[str],
                "skills_with_credibility": list[dict],  # {skill_name, credibility_score}
                "embedding": list[float],
                "implicit_skills": list[str],
            }
            job_requirement: 岗位需求 {
                "title": str,
                "required_skills": list[str],
                "optional_skills": list[str],
                "embedding": list[float],
            }
        """
        resume_skills = set(resume_profile.get("skills", []))
        resume_implicit = set(resume_profile.get("implicit_skills", []))
        all_resume_skills = resume_skills | resume_implicit

        required = set(job_requirement.get("required_skills", []))
        optional = set(job_requirement.get("optional_skills", []))

        # 1. 技能匹配分
        skill_score, matched, missing_crit, missing_opt = self._calc_skill_match(
            all_resume_skills, required, optional, resume_profile
        )

        # 2. 图谱路径分
        graph_score = self._calc_graph_distance(all_resume_skills, required)

        # 3. 向量相似分
        vector_score = self._calc_vector_similarity(
            resume_profile.get("embedding"),
            job_requirement.get("embedding")
        )

        # 4. 趋势加分
        trend_score = self._calc_trend_bonus(all_resume_skills)

        # 5. 可信度修正
        cred_score = self._calc_credibility_adjustment(
            resume_profile.get("skills_with_credibility", [])
        )

        # 6. 数据新鲜度调整（非必须字段）
        data_freshness = job_requirement.get("data_freshness", 1.0)
        data_age_days = job_requirement.get("data_age_days")

        # 加权求和
        scores = {
            "skill": skill_score,
            "graph": graph_score,
            "vector": vector_score,
            "trend": trend_score,
            "credibility": cred_score,
        }

        raw_score = sum(
            scores[k] * self.weights[k]
            for k in self.weights
        )

        # 新鲜度作为最终分调整系数
        freshness_multiplier = 0.5 + data_freshness
        final_score = raw_score * freshness_multiplier

        # 新鲜度文本说明
        age_info = ""
        if data_age_days is not None:
            if data_age_days <= 7:
                age_info = "本周采集"
            elif data_age_days <= 30:
                age_info = f"约{data_age_days}天前采集"
            elif data_age_days <= 90:
                age_info = f"约{data_age_days}天前采集（数据较旧）"
            else:
                age_info = f"超过{data_age_days}天未更新，建议重新采集"

        explanation = self._generate_explanation(
            job_requirement["title"], final_score, scores,
            matched, missing_crit, missing_opt,
        )

        return MatchResult(
            score=round(min(final_score, 1.0), 4),
            job_title=job_requirement["title"],
            breakdown={
                **{k: round(v, 4) for k, v in scores.items()},
                "coefficient": round(freshness_multiplier, 4),
            },
            matched_skills=matched,
            missing_critical=missing_crit,
            missing_optional=missing_opt,
            explanation=f"[{age_info}] {explanation}" if age_info else explanation,
        )

    def batch_calculate(self, resume_profile: dict,
                        jobs: list[dict]) -> list[MatchResult]:
        """批量计算匹配度"""
        results = []
        for job in jobs:
            try:
                result = self.calculate_match(resume_profile, job)
                results.append(result)
            except Exception as e:
                logger.error(f"匹配计算失败[{job.get('title')}]: {e}")
        return sorted(results, key=lambda r: r.score, reverse=True)

    def _calc_skill_match(self, resume_skills: set, required: set, optional: set,
                          resume_profile: dict) -> tuple[float, list, list, list]:
        """计算技能匹配分"""
        cred_map = {}
        for swc in resume_profile.get("skills_with_credibility", []):
            cred_map[swc.get("skill_name", "")] = swc.get("credibility_score", 0.5)

        # 必备技能匹配
        matched_required = []
        missing_required = []
        for skill in required:
            # 精确匹配
            if skill in resume_skills:
                matched_required.append(skill)
            # 模糊匹配（检查相似技能）
            elif self._find_similar(skill, resume_skills):
                matched_required.append(f"{skill}(相似)")
            else:
                missing_required.append(skill)

        # 可选技能匹配
        matched_optional = []
        for skill in optional:
            if skill in resume_skills:
                matched_optional.append(skill)

        all_matched = matched_required + matched_optional

        # 计算加权覆盖率
        required_coverage = len(matched_required) / max(len(required), 1)
        optional_coverage = len(matched_optional) / max(len(optional), 1)

        # 考虑可信度权重
        cred_weighted = 0
        for skill in all_matched:
            cred = cred_map.get(skill, cred_map.get(skill.replace("(相似)", ""), 0.7))
            cred_weighted += cred
        avg_cred = cred_weighted / max(len(all_matched), 1) if all_matched else 0

        # 最终技能分 = 必备覆盖率×0.6 + 可选覆盖率×0.25 + 可信度×0.15
        skill_score = required_coverage * 0.6 + optional_coverage * 0.25 + avg_cred * 0.15

        return skill_score, all_matched, missing_required, list(optional - set(matched_optional))

    def _find_similar(self, target: str, skill_set: set) -> Optional[str]:
        """在技能集中查找相似技能"""
        target_lower = target.lower()
        for skill in skill_set:
            skill_lower = skill.lower()
            # 精确子串匹配
            if target_lower in skill_lower or skill_lower in target_lower:
                return skill
            # 常见别名
            aliases = {
                "pytorch": ["torch"],
                "tensorflow": ["tf"],
                "javascript": ["js"],
                "typescript": ["ts"],
                "kubernetes": ["k8s"],
            }
            if target_lower in aliases and skill_lower in aliases[target_lower]:
                return skill
        return None

    def _calc_graph_distance(self, resume_skills: set, required: set) -> float:
        """基于图谱距离的评分"""
        if not self.graph.is_connected:
            return 0.5  # 无图谱时返回中性分

        total_distance = 0
        comparisons = 0

        for req_skill in required:
            for res_skill in resume_skills:
                paths = self.graph.find_path_between_skills(req_skill, res_skill)
                if paths:
                    dist = paths[0].get("distance", 10)
                    total_distance += dist
                    comparisons += 1

        if comparisons == 0:
            return 0.3

        avg_distance = total_distance / comparisons
        # 距离越近分数越高
        return max(0, 1.0 - avg_distance / 6.0)

    def _calc_vector_similarity(self, resume_emb: list, job_emb: list) -> float:
        """向量余弦相似度"""
        if not resume_emb or not job_emb:
            return 0.5

        import numpy as np
        v1 = np.array(resume_emb)
        v2 = np.array(job_emb)

        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        cosine = np.dot(v1, v2) / (norm1 * norm2)
        return float((cosine + 1) / 2)  # 归一化到0-1

    def _calc_trend_bonus(self, skills: set) -> float:
        """趋势加分 - 掌握高趋势技能的奖励"""
        if not self.graph.is_connected:
            return 0.5

        trend_sum = 0
        count = 0
        for skill in skills:
            # 查询技能的趋势分数
            result = self.graph.execute_query("""
                MATCH (s:Skill {name: $name}) RETURN s.trend_score
            """, {"name": skill})
            if result and result[0].get("trend_score") is not None:
                trend_sum += (result[0]["trend_score"] + 1) / 2  # 归一化 -1~1 → 0~1
                count += 1

        return trend_sum / max(count, 1) if count > 0 else 0.5

    def _calc_credibility_adjustment(self, skills_with_cred: list) -> float:
        """可信度修正"""
        if not skills_with_cred:
            return 0.5

        total = sum(s.get("credibility_score", 0.5) for s in skills_with_cred)
        return total / len(skills_with_cred)

    def _generate_explanation(self, job_title: str, score: float, breakdown: dict,
                               matched: list, missing_crit: list, missing_opt: list) -> str:
        """生成匹配解释"""
        parts = [f"### 与「{job_title}」的匹配分析\n"]
        parts.append(f"**总体匹配度**: {score:.1%}\n")

        # 分数构成
        parts.append("**分数构成**:\n")
        for component, value in breakdown.items():
            names = {"skill": "技能匹配", "graph": "图谱关联", "vector": "语义相似",
                    "trend": "趋势红利", "credibility": "可信度"}
            bar = "█" * int(value * 20) + "░" * (20 - int(value * 20))
            parts.append(f"- {names.get(component, component)}: {value:.1%} {bar}\n")

        # 匹配的技能
        if matched:
            parts.append(f"\n**已匹配技能** ({len(matched)}个): {', '.join(matched[:10])}")
            if len(matched) > 10:
                parts.append(f" 等{len(matched)-10}个...")

        # 缺失的关键技能
        if missing_crit:
            parts.append(f"\n**关键差距** ({len(missing_crit)}个): ")
            parts.append(", ".join(missing_crit))

        # 缺失的可选技能
        if missing_opt:
            parts.append(f"\n**可选补充** ({len(missing_opt)}个): ")
            parts.append(", ".join(missing_opt[:8]))

        return "".join(parts)
