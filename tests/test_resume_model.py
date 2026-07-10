"""简历模型测试 - ResumeProfile、SkillWithCredibility 等"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from models.resume_model import (
    CredibilityLevel, SkillWithCredibility, ProjectExperience,
    WorkExperience, EducationRecord, ResumeProfile,
)


class TestCredibilityLevel:
    """CredibilityLevel 枚举测试"""

    def test_values(self):
        """测试 CredibilityLevel 枚举值"""
        assert CredibilityLevel.EXPLICIT_CERTIFIED.value == "explicit_certified"
        assert CredibilityLevel.EXPLICIT_PROJECT.value == "explicit_project"
        assert CredibilityLevel.IMPLICIT_INFERRED.value == "implicit_inferred"
        assert CredibilityLevel.MENTIONED_ONLY.value == "mentioned_only"
        assert CredibilityLevel.SELF_CLAIMED.value == "self_claimed"

    def test_order(self):
        """测试枚举顺序"""
        levels = list(CredibilityLevel)
        assert levels == [
            CredibilityLevel.EXPLICIT_CERTIFIED,
            CredibilityLevel.EXPLICIT_PROJECT,
            CredibilityLevel.IMPLICIT_INFERRED,
            CredibilityLevel.MENTIONED_ONLY,
            CredibilityLevel.SELF_CLAIMED,
        ]


class TestSkillWithCredibility:
    """SkillWithCredibility 模型测试"""

    def test_create_minimal(self):
        """测试最小字段创建"""
        skill = SkillWithCredibility(
            skill_name="Python",
            credibility_level=CredibilityLevel.EXPLICIT_PROJECT,
            credibility_score=0.85,
        )
        assert skill.skill_name == "Python"
        assert skill.credibility_level == CredibilityLevel.EXPLICIT_PROJECT
        assert skill.credibility_score == 0.85
        assert skill.evidence is None
        assert skill.proficiency_level is None

    def test_create_full(self):
        """测试全字段创建"""
        skill = SkillWithCredibility(
            skill_name="Kubernetes",
            credibility_level=CredibilityLevel.EXPLICIT_CERTIFIED,
            credibility_score=1.0,
            evidence="持有CKA认证",
            proficiency_level=9,
        )
        assert skill.proficiency_level == 9
        assert skill.evidence == "持有CKA认证"

    def test_credibility_score_range(self):
        """测试 credibility_score 范围验证"""
        with pytest.raises(ValidationError):
            SkillWithCredibility(
                skill_name="Bad",
                credibility_level=CredibilityLevel.MENTIONED_ONLY,
                credibility_score=1.5,
            )

        with pytest.raises(ValidationError):
            SkillWithCredibility(
                skill_name="Bad",
                credibility_level=CredibilityLevel.MENTIONED_ONLY,
                credibility_score=-0.1,
            )

    def test_proficiency_level_range(self):
        """测试 proficiency_level 范围验证"""
        with pytest.raises(ValidationError):
            SkillWithCredibility(
                skill_name="Bad",
                credibility_level=CredibilityLevel.MENTIONED_ONLY,
                credibility_score=0.5,
                proficiency_level=0,
            )

        with pytest.raises(ValidationError):
            SkillWithCredibility(
                skill_name="Bad",
                credibility_level=CredibilityLevel.MENTIONED_ONLY,
                credibility_score=0.5,
                proficiency_level=11,
            )

    def test_default_proficiency(self):
        """测试默认 proficiency 为 None"""
        skill = SkillWithCredibility(
            skill_name="Python",
            credibility_level=CredibilityLevel.MENTIONED_ONLY,
            credibility_score=0.4,
        )
        assert skill.proficiency_level is None


class TestProjectExperience:
    """ProjectExperience 模型测试"""

    def test_create_minimal(self):
        """测试最小字段创建"""
        proj = ProjectExperience(project_name="知识图谱系统")
        assert proj.project_name == "知识图谱系统"
        assert proj.description == ""
        assert proj.complexity_score == 0.5
        assert proj.technologies_used == []
        assert proj.red_flags == []
        assert proj.strengths == []

    def test_create_full(self):
        """测试全字段创建"""
        proj = ProjectExperience(
            project_name="智能推荐系统",
            role="技术负责人",
            start_date="2023-01",
            end_date="2024-06",
            description="基于深度学习的推荐系统",
            technologies_used=["Python", "PyTorch", "Redis"],
            complexity_score=0.85,
            tech_depth_scores={"Python": 9, "PyTorch": 8},
            red_flags=["时间线模糊"],
            strengths=["高并发处理"],
        )
        assert proj.role == "技术负责人"
        assert len(proj.technologies_used) == 3
        assert proj.tech_depth_scores["Python"] == 9

    def test_complexity_score_range(self):
        """测试 complexity_score 范围验证"""
        with pytest.raises(ValidationError):
            ProjectExperience(
                project_name="Bad",
                complexity_score=2.0,
            )

    def test_tech_depth_scores_default(self):
        """测试 tech_depth_scores 默认空字典"""
        proj = ProjectExperience(project_name="Test")
        assert proj.tech_depth_scores == {}


class TestWorkExperience:
    """WorkExperience 模型测试"""

    def test_create_minimal(self):
        """测试最小字段创建"""
        work = WorkExperience(company="字节跳动", position="后端工程师")
        assert work.company == "字节跳动"
        assert work.position == "后端工程师"
        assert work.description == ""

    def test_create_full(self):
        """测试全字段创建"""
        work = WorkExperience(
            company="阿里巴巴",
            position="高级工程师",
            start_date="2020-03",
            end_date="至今",
            description="负责电商平台后端开发",
            department="电商事业部",
        )
        assert work.department == "电商事业部"


class TestEducationRecord:
    """EducationRecord 模型测试"""

    def test_create_minimal(self):
        """测试最小字段创建"""
        edu = EducationRecord(school="清华大学", degree="硕士", major="计算机科学")
        assert edu.school == "清华大学"
        assert edu.degree == "硕士"
        assert edu.gpa is None

    def test_create_with_gpa(self):
        """测试带 GPA 的教育记录"""
        edu = EducationRecord(
            school="北京大学",
            degree="学士",
            major="软件工程",
            graduation_date="2020-07",
            gpa=3.8,
        )
        assert edu.gpa == 3.8


class TestResumeProfile:
    """ResumeProfile 模型测试"""

    def test_create_minimal(self):
        """测试最小字段创建"""
        profile = ResumeProfile()
        assert profile.name is None
        assert profile.education == []
        assert profile.work_experience == []
        assert profile.projects == []
        assert profile.skills_explicit == []
        assert profile.skills_implicit == []
        assert profile.skills_with_credibility == []
        assert profile.total_experience_years == 0.0
        assert profile.overall_technical_level == "mid"
        assert profile.diversity_score == 0.0
        assert profile.growth_potential == 0.5
        assert isinstance(profile.parsed_at, datetime)

    def test_create_full(self):
        """测试全字段创建"""
        profile = ResumeProfile(
            name="张三",
            phone="13800138000",
            email="zhangsan@example.com",
            age=28,
            education=[
                EducationRecord(school="清华大学", degree="硕士", major="计算机科学"),
            ],
            work_experience=[
                WorkExperience(company="字节跳动", position="后端工程师"),
            ],
            projects=[
                ProjectExperience(project_name="智能系统", technologies_used=["Python"]),
            ],
            skills_explicit=["Python", "Java"],
            skills_implicit=["Docker", "K8s"],
            skills_with_credibility=[
                SkillWithCredibility(
                    skill_name="Python",
                    credibility_level=CredibilityLevel.EXPLICIT_PROJECT,
                    credibility_score=0.9,
                ),
            ],
            total_experience_years=5.0,
            overall_technical_level="senior",
            diversity_score=0.8,
            growth_potential=0.9,
        )
        assert profile.name == "张三"
        assert len(profile.education) == 1
        assert len(profile.work_experience) == 1
        assert len(profile.projects) == 1
        assert len(profile.skills_explicit) == 2
        assert profile.total_experience_years == 5.0

    def test_empty_education(self):
        """测试空教育背景"""
        profile = ResumeProfile(education=[])
        assert profile.education == []

    def test_default_hash_empty_string(self):
        """测试 resume_hash 默认值为空字符串"""
        profile = ResumeProfile()
        assert profile.resume_hash == ""
