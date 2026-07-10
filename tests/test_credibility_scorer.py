"""可信度评分器测试 - CredibilityScorer"""

import pytest
from models.resume_model import CredibilityLevel
from core.credibility_scorer import CredibilityScorer, CREDIBILITY_DEFINITIONS


class TestCredibilityDefinitions:
    """可信度定义测试"""

    def test_all_levels_defined(self):
        """测试所有CredibilityLevel都有定义"""
        for level in CredibilityLevel:
            assert level in CREDIBILITY_DEFINITIONS
            assert "score" in CREDIBILITY_DEFINITIONS[level]
            assert "description" in CREDIBILITY_DEFINITIONS[level]

    def test_explicit_certified_score(self):
        """测试认证级别分数"""
        assert CREDIBILITY_DEFINITIONS[CredibilityLevel.EXPLICIT_CERTIFIED]["score"] == 1.0

    def test_self_claimed_score(self):
        """测试自称级别分数"""
        assert CREDIBILITY_DEFINITIONS[CredibilityLevel.SELF_CLAIMED]["score"] == 0.20

    def test_score_descending(self):
        """测试分数递减顺序"""
        scores = [CREDIBILITY_DEFINITIONS[level]["score"] for level in CredibilityLevel]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]


class TestAssessSkill:
    """assess_skill 方法测试"""

    @pytest.fixture
    def scorer(self):
        return CredibilityScorer()

    def test_certification_location(self, scorer):
        """测试认证区域"""
        result = scorer.assess_skill("AWS", "AWS认证架构师", "certification")
        assert result.credibility_level == CredibilityLevel.EXPLICIT_CERTIFIED
        assert result.credibility_score >= 0.9

    def test_project_with_action_verb(self, scorer):
        """测试项目经验中有动作动词"""
        result = scorer.assess_skill("Redis", "使用Redis实现了分布式缓存", "project")
        assert result.credibility_level == CredibilityLevel.EXPLICIT_PROJECT
        assert result.credibility_score >= 0.8

    def test_project_without_action(self, scorer):
        """测试项目经验中无动作动词"""
        result = scorer.assess_skill("Redis", "Redis缓存", "project")
        assert result.credibility_level == CredibilityLevel.MENTIONED_ONLY

    def test_skills_section_strong_claim(self, scorer):
        """测试技能栏夸大声称"""
        result = scorer.assess_skill("Kubernetes", "精通Kubernetes", "skills_section")
        assert result.credibility_level == CredibilityLevel.SELF_CLAIMED

    def test_skills_section_moderate(self, scorer):
        """测试技能栏适度声称"""
        result = scorer.assess_skill("Python", "熟练掌握Python", "skills_section")
        assert result.credibility_level == CredibilityLevel.MENTIONED_ONLY

    def test_skills_section_plain(self, scorer):
        """测试技能栏无修饰词"""
        result = scorer.assess_skill("Python", "Python", "skills_section")
        assert result.credibility_level == CredibilityLevel.MENTIONED_ONLY

    def test_inferred_location(self, scorer):
        """测试推断来源"""
        result = scorer.assess_skill("Docker", "做微服务项目", "inferred")
        assert result.credibility_level == CredibilityLevel.IMPLICIT_INFERRED
        assert 0.5 <= result.credibility_score <= 0.8

    def test_unknown_location(self, scorer):
        """测试未知来源"""
        result = scorer.assess_skill("Python", "Python", "unknown")
        assert result.credibility_level == CredibilityLevel.MENTIONED_ONLY

    def test_detail_bonus_with_numbers(self, scorer):
        """测试数字量化加分"""
        result = scorer.assess_skill(
            "Redis",
            "使用Redis构建了缓存系统，将查询性能提升了300%，QPS从1000提升到5000",
            "project",
        )
        assert result.credibility_score > 0.85

    def test_long_context_bonus(self, scorer):
        """测试长描述加分"""
        context = "负责设计和实现了基于微服务架构的电商平台后端系统，使用Spring Cloud框架，" * 5
        result = scorer.assess_skill("Spring Cloud", context, "project")
        assert result.credibility_score > 0.8

    def test_consistency_positive(self, scorer):
        """测试一致性正面信号加分"""
        result = scorer.assess_skill(
            "Kubernetes",
            "使用Kubernetes部署了生产环境，系统上线运行效果良好",
            "project",
        )
        assert result.credibility_score > 0.8

    def test_consistency_negative_learning(self, scorer):
        """测试一致性负面信号扣分"""
        result = scorer.assess_skill(
            "Kubernetes",
            "正在学习Kubernetes，了解一些基本概念",
            "skills_section",
        )
        assert result.credibility_score < 0.5

    def test_proficiency_estimated(self, scorer):
        """测试熟练度估算"""
        result = scorer.assess_skill("Python", "精通Python并有多年经验", "skills_section")
        assert result.proficiency_level is not None
        assert 1 <= result.proficiency_level <= 10


class TestAssessBatch:
    """批量评估测试"""

    @pytest.fixture
    def scorer(self):
        return CredibilityScorer()

    def test_batch_assessment(self, scorer):
        """测试批量评估"""
        skills_data = [
            ("Python", "使用Python开发了推荐系统", "project"),
            ("Docker", "Docker容器化部署", "skills_section"),
            ("AWS", "AWS认证架构师", "certification"),
        ]
        results = scorer.assess_batch(skills_data)
        assert len(results) == 3
        assert results[0].skill_name == "Python"
        assert results[2].skill_name == "AWS"
        assert results[2].credibility_level == CredibilityLevel.EXPLICIT_CERTIFIED

    def test_batch_empty(self, scorer):
        """测试空批处理"""
        results = scorer.assess_batch([])
        assert results == []


class TestGetOverallCredibility:
    """整体可信度测试"""

    @pytest.fixture
    def scorer(self):
        return CredibilityScorer()

    def test_overall_empty(self, scorer):
        """测试空列表"""
        result = scorer.get_overall_credibility([])
        assert result["overall_score"] == 0
        assert "breakdown" in result

    def test_overall_with_skills(self, scorer):
        """测试有技能时的整体可信度"""
        skills = [
            scorer.assess_skill("Python", "精通Python", "skills_section"),
            scorer.assess_skill("Docker", "使用Docker部署", "project"),
            scorer.assess_skill("AWS", "AWS认证", "certification"),
        ]
        result = scorer.get_overall_credibility(skills)
        assert result["total_skills"] == 3
        assert 0 < result["overall_score"] <= 1.0
        assert "explicit_certified" in result["breakdown"]
        assert "self_claimed" in result["breakdown"]

    def test_high_confidence_count(self, scorer):
        """测试高置信度计数"""
        skills = [
            scorer.assess_skill("Python", "使用Python开发了推荐系统", "project"),
            scorer.assess_skill("Docker", "Docker容器化", "skills_section"),
        ]
        result = scorer.get_overall_credibility(skills)
        assert "high_confidence_count" in result
        assert "low_confidence_count" in result
