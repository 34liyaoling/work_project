"""可信度评分器 - 对技能声明进行可信度评估"""

import logging
import re
from typing import Optional
from models.resume_model import CredibilityLevel, SkillWithCredibility

logger = logging.getLogger(__name__)


# 可信度级别的详细定义
CREDIBILITY_DEFINITIONS = {
    CredibilityLevel.EXPLICIT_CERTIFIED: {
        "score": 1.0,
        "description": "有权威证书/认证证明",
        "examples": ["AWS认证架构师", "PMP证书", "CKA认证", "CFA", "软考高级"],
        "keywords": ["认证", "证书", "持证", "通过考试", "获得.*认证", ".*Certified"],
    },
    CredibilityLevel.EXPLICIT_PROJECT: {
        "score": 0.85,
        "description": "在项目经验中明确使用并描述细节",
        "examples": ["使用Redis实现了分布式缓存", "基于Kafka构建了消息管道"],
        "keywords": ["实现", "搭建", "构建", "开发了", "设计了", "部署了", "优化了"],
    },
    CredibilityLevel.IMPLICIT_INFERRED: {
        "score": 0.65,
        "description": "从项目描述合理推断但未明确提及",
        "examples": ["做微服务→推断懂Docker", "做高并发→推断懂Redis"],
        "keywords": [],
    },
    CredibilityLevel.MENTIONED_ONLY: {
        "score": 0.40,
        "description": "仅在技能列表栏中列出，无使用细节",
        "examples": ["技能栏写了Kubernetes"],
        "keywords": ["熟练掌握", "熟悉", "了解", "掌握"],
    },
    CredibilityLevel.SELF_CLAIMED: {
        "score": 0.20,
        "description": "自我声称但无任何佐证材料",
        "examples": ["自称精通但无项目支撑"],
        "keywords": ["精通", "专家", "非常熟悉", "深入了解"],
    },
}


class CredibilityScorer:
    """技能声明可信度评分器

    对简历中的每个技能声明进行多维度可信度评估：
    1. 来源位置（技能栏 vs 项目经验 vs 证书）
    2. 描述细节程度（有具体场景 vs 笼统描述）
    3. 上下文支持（是否有相关项目/成果佐证）
    4. 时间新鲜度（最近使用的技能更可信）
    """

    def __init__(self):
        self.definitions = CREDIBILITY_DEFINITIONS

    def assess_skill(self, skill_name: str, context: str = "",
                     location: str = "skills_section") -> SkillWithCredibility:
        """评估单个技能的可信度

        Args:
            skill_name: 技能名称
            context: 包含该技能的上下文文本
            location: 技能出现的位置 (skills_section/project/certification/inferred)

        Returns:
            带可信度评级的技能对象
        """
        # 确定基础级别
        base_level = self._determine_base_level(skill_name, context, location)
        base_score = self.definitions[base_level]["score"]

        # 细节加成分
        detail_bonus = self._calculate_detail_bonus(context)

        # 上下文一致性的调整
        consistency_adj = self._check_context_consistency(skill_name, context)

        # 最终得分
        final_score = min(1.0, max(0.0, base_score + detail_bonus + consistency_adj))

        # 确定熟练度（粗略估计）
        proficiency = self._estimate_proficiency(skill_name, context, final_score)

        return SkillWithCredibility(
            skill_name=skill_name,
            credibility_level=base_level,
            credibility_score=round(final_score, 2),
            evidence=context[:200] if context else None,
            proficiency_level=proficiency,
        )

    def assess_batch(self, skills_with_context: list[tuple[str, str, str]]) -> list[SkillWithCredibility]:
        """批量评估技能可信度

        Args:
            skills_with_context: [(skill_name, context, location), ...]
        """
        results = []
        for skill_name, context, location in skills_with_context:
            result = self.assess_skill(skill_name, context, location)
            results.append(result)
        return results

    def _determine_base_level(self, skill_name: str, context: str,
                              location: str) -> CredibilityLevel:
        """确定基础可信度级别"""
        # 证书区域
        if location == "certification":
            return CredibilityLevel.EXPLICIT_CERTIFIED

        # 项目经验区域且有动作动词
        if location == "project":
            action_verbs = ["实现", "搭建", "构建", "开发", "设计", "部署", "优化",
                          "重构", "迁移", "集成", "定制", "改造"]
            if any(verb in context for verb in action_verbs):
                return CredibilityLevel.EXPLICIT_PROJECT
            return CredibilityLevel.MENTIONED_ONLY

        # 技能列表区域
        if location == "skills_section":
            # 检测是否有程度修饰词
            strong_claims = ["精通", "专家", "非常熟悉", "深入了解"]
            moderate_claims = ["熟练掌握", "熟悉", "掌握", "了解"]

            context_lower = (context + " " + skill_name).lower()
            if any(claim in context_lower for claim in strong_claims):
                return CredibilityLevel.SELF_CLAIMED
            elif any(claim in context_lower for claim in moderate_claims):
                return CredibilityLevel.MENTIONED_ONLY
            return CredibilityLevel.MENTIONED_ONLY

        # 推断得到的
        if location == "inferred":
            return CredibilityLevel.IMPLICIT_INFERRED

        return CredibilityLevel.MENTIONED_ONLY

    def _calculate_detail_bonus(self, context: str) -> float:
        """基于描述细节程度的加分"""
        if not context:
            return 0.0

        bonus = 0.0

        # 具体数字（量化成果）
        numbers = re.findall(r'\d+[\.]?\d*\s*(?:%|万|亿|K|ms|秒|天|人|次|QPS|TPS)', context)
        bonus += min(len(numbers) * 0.03, 0.10)

        # 具体技术名词
        tech_terms = re.findall(r'[A-Z][a-zA-Z]+|[A-Z]{2,}', context)
        bonus += min(len(tech_terms) * 0.01, 0.05)

        # 问题-解决方案模式
        problem_solution_patterns = [
            r'解决了?.*?问题',
            r'.*?优化.*?(?:性能|速度|效率).*?\d+',
            r'.*?降低了?.*?(?:成本|延迟|耗时).*?\d+',
            r'.*?提升.*?(?:效率|吞吐量|覆盖率).*?\d+',
        ]
        for pattern in problem_solution_patterns:
            if re.search(pattern, context):
                bonus += 0.05
                break

        # 长度奖励（较长的描述通常意味着更多细节）
        if len(context) > 100:
            bonus += 0.02
        elif len(context) > 200:
            bonus += 0.04

        return round(bonus, 2)

    def _check_context_consistency(self, skill_name: str, context: str) -> float:
        """检查上下文中技能声明的一致性"""
        if not context:
            return 0.0

        adj = 0.0

        # 正面信号
        positive_signals = ["成功", "效果良好", "上线运行", "投入使用",
                          "得到认可", "推广使用", "生产环境"]
        for signal in positive_signals:
            if signal in context:
                adj += 0.02

        # 负面信号（矛盾或模糊）
        negative_signals = ["学习", "正在学习", "计划学习", "准备学习",
                          "了解一些", "稍微知道", "接触过"]
        for signal in negative_signals:
            if signal in context:
                adj -= 0.05

        # 过度声明检测
        if "精通" in context and len(context) < 50:
            adj -= 0.10  # 声称精通但描述很短

        return round(adj, 2)

    def _estimate_proficiency(self, skill_name: str, context: str,
                              credibility_score: float) -> Optional[int]:
        """估算技能熟练度(1-10)"""
        base = int(credibility_score * 8) + 1  # 将0-1映射到1-9

        # 根据修饰词调整
        if "精通" in context or "专家" in context:
            base = min(base + 2, 10)
        elif "熟悉" in context or "熟练" in context:
            base = min(base + 1, 10)
        elif "了解" in context or "接触" in context:
            base = max(base - 2, 1)

        return max(1, min(10, base))

    def get_overall_credibility(self, skills: list[SkillWithCredibility]) -> dict:
        """计算整体可信度概况"""
        if not skills:
            return {"overall_score": 0, "breakdown": {}}

        total_score = sum(s.credibility_score for s in skills)
        weighted_avg = total_score / len(skills)

        breakdown = {}
        for level in CredibilityLevel:
            level_skills = [s for s in skills if s.credibility_level == level]
            breakdown[level.value] = {
                "count": len(level_skills),
                "avg_score": round(sum(s.credibility_score for s in level_skills) / len(level_skills), 2) if level_skills else 0,
            }

        return {
            "overall_score": round(weighted_avg, 2),
            "total_skills": len(skills),
            "high_confidence_count": len([s for s in skills if s.credibility_score >= 0.7]),
            "low_confidence_count": len([s for s in skills if s.credibility_score < 0.4]),
            "breakdown": breakdown,
        }
