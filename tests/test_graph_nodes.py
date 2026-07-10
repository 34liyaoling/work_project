"""图节点模型测试 - SkillNode、JobNode、GraphTriple"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from models.graph_nodes import (
    SkillNode, SkillCategory, SkillDomain, LifecycleStage,
    JobNode, JobStatus, GraphTriple,
    DomainNode, PersonNode,
)


class TestSkillNode:
    """SkillNode 模型测试"""

    def test_create_minimal(self):
        """测试 SkillNode 最小字段创建"""
        node = SkillNode(
            name="Python",
            category=SkillCategory.PROGRAMMING_LANGUAGE,
            domain=SkillDomain.ARTIFICIAL_INTELLIGENCE,
        )
        assert node.name == "Python"
        assert node.category == SkillCategory.PROGRAMMING_LANGUAGE
        assert node.domain == SkillDomain.ARTIFICIAL_INTELLIGENCE
        assert node.difficulty == 5
        assert node.trend_score == 0.0
        assert node.lifecycle == LifecycleStage.GROWING
        assert node.confidence == 0.8
        assert node.version == "1.0"
        assert isinstance(node.last_updated, datetime)

    def test_create_full(self):
        """测试 SkillNode 全字段创建"""
        node = SkillNode(
            name="Kubernetes",
            category=SkillCategory.CLOUD_SERVICE,
            domain=SkillDomain.CLOUD_COMPUTING,
            difficulty=8,
            trend_score=0.9,
            lifecycle=LifecycleStage.GROWING,
            version="2.0",
            confidence=0.95,
            sources=["Boss直聘", "拉勾"],
            related_jobs=["运维工程师", "云原生架构师"],
            description="容器编排平台",
            aliases=["K8s", "Kube"],
        )
        assert node.name == "Kubernetes"
        assert node.difficulty == 8
        assert node.trend_score == 0.9
        assert len(node.sources) == 2
        assert len(node.aliases) == 2

    def test_difficulty_range(self):
        """测试 difficulty 字段范围验证"""
        with pytest.raises(ValidationError):
            SkillNode(
                name="Bad",
                category=SkillCategory.TOOL,
                domain=SkillDomain.DEVOPS,
                difficulty=0,
            )

        with pytest.raises(ValidationError):
            SkillNode(
                name="Bad",
                category=SkillCategory.TOOL,
                domain=SkillDomain.DEVOPS,
                difficulty=11,
            )

    def test_confidence_range(self):
        """测试 confidence 字段范围验证"""
        with pytest.raises(ValidationError):
            SkillNode(
                name="Bad",
                category=SkillCategory.TOOL,
                domain=SkillDomain.DEVOPS,
                confidence=-0.1,
            )

        with pytest.raises(ValidationError):
            SkillNode(
                name="Bad",
                category=SkillCategory.TOOL,
                domain=SkillDomain.DEVOPS,
                confidence=1.5,
            )

    def test_trend_score_range(self):
        """测试 trend_score 字段范围验证"""
        with pytest.raises(ValidationError):
            SkillNode(
                name="Bad",
                category=SkillCategory.TOOL,
                domain=SkillDomain.DEVOPS,
                trend_score=-2.0,
            )

    def test_all_categories(self):
        """测试所有 SkillCategory 枚举值"""
        expected = [
            SkillCategory.PROGRAMMING_LANGUAGE,
            SkillCategory.FRAMEWORK,
            SkillCategory.TOOL,
            SkillCategory.DATABASE,
            SkillCategory.MIDDLEWARE,
            SkillCategory.CLOUD_SERVICE,
            SkillCategory.AI_ML,
            SkillCategory.SOFT_SKILL,
            SkillCategory.DOMAIN_KNOWLEDGE,
            SkillCategory.OTHER,
        ]
        assert list(SkillCategory) == expected

    def test_all_domains(self):
        """测试所有 SkillDomain 枚举值"""
        expected = [
            SkillDomain.ARTIFICIAL_INTELLIGENCE,
            SkillDomain.BIG_DATA,
            SkillDomain.CLOUD_COMPUTING,
            SkillDomain.BLOCKCHAIN,
            SkillDomain.IOT,
            SkillDomain.CYBERSECURITY,
            SkillDomain.SOFTWARE_DEVELOPMENT,
            SkillDomain.MOBILE_DEVELOPMENT,
            SkillDomain.DEVOPS,
            SkillDomain.DATA_SCIENCE,
        ]
        assert list(SkillDomain) == expected

    def test_default_lifecycle(self):
        """测试默认生命周期为 GROWING"""
        node = SkillNode(
            name="Python",
            category=SkillCategory.PROGRAMMING_LANGUAGE,
            domain=SkillDomain.ARTIFICIAL_INTELLIGENCE,
        )
        assert node.lifecycle == LifecycleStage.GROWING


class TestLifecycleStage:
    """LifecycleStage 枚举测试"""

    def test_values(self):
        """测试 LifecycleStage 枚举值"""
        assert LifecycleStage.EMERGING.value == "emerging"
        assert LifecycleStage.GROWING.value == "growing"
        assert LifecycleStage.MATURE.value == "mature"
        assert LifecycleStage.DECLINING.value == "declining"
        assert LifecycleStage.OBSOLETE.value == "obsolete"

    def test_order(self):
        """测试枚举顺序"""
        stages = list(LifecycleStage)
        assert stages == [
            LifecycleStage.EMERGING,
            LifecycleStage.GROWING,
            LifecycleStage.MATURE,
            LifecycleStage.DECLINING,
            LifecycleStage.OBSOLETE,
        ]


class TestJobNode:
    """JobNode 模型测试"""

    def test_create_minimal(self):
        """测试 JobNode 最小字段创建"""
        node = JobNode(
            title="AI算法工程师",
            domain=SkillDomain.ARTIFICIAL_INTELLIGENCE,
        )
        assert node.title == "AI算法工程师"
        assert node.domain == SkillDomain.ARTIFICIAL_INTELLIGENCE
        assert node.status == JobStatus.ACTIVE
        assert node.education_requirement == "本科"
        assert node.experience_range == (1, 3)

    def test_create_full(self):
        """测试 JobNode 全字段创建"""
        node = JobNode(
            title="云原生架构师",
            domain=SkillDomain.CLOUD_COMPUTING,
            status=JobStatus.ACTIVE,
            required_skills=["Kubernetes", "Docker", "Istio"],
            optional_skills=["Prometheus", "Grafana"],
            avg_salary_min=50,
            avg_salary_max=100,
            experience_range=(5, 10),
            education_requirement="硕士",
            demand_trend="rising",
            responsibilities=["设计云原生架构", "容器化改造"],
            companies_hiring=["字节跳动", "阿里巴巴"],
        )
        assert len(node.required_skills) == 3
        assert len(node.optional_skills) == 2
        assert node.avg_salary_min == 50
        assert node.avg_salary_max == 100

    def test_job_status_values(self):
        """测试 JobStatus 枚举值"""
        assert JobStatus.ACTIVE.value == "active"
        assert JobStatus.CANDIDATE.value == "candidate"
        assert JobStatus.ARCHIVED.value == "archived"

    def test_candidate_status(self):
        """测试候选状态岗位"""
        node = JobNode(
            title="新岗位",
            domain=SkillDomain.BIG_DATA,
            status=JobStatus.CANDIDATE,
        )
        assert node.status == JobStatus.CANDIDATE


class TestDomainNode:
    """DomainNode 模型测试"""

    def test_create_minimal(self):
        """测试 DomainNode 最小字段创建"""
        node = DomainNode(name="人工智能")
        assert node.name == "人工智能"
        assert node.parent_domain is None
        assert node.trend_score == 0.0

    def test_create_with_parent(self):
        """测试带父领域的 DomainNode"""
        node = DomainNode(
            name="深度学习",
            parent_domain="人工智能",
            description="深度学习子领域",
            trend_score=0.8,
        )
        assert node.parent_domain == "人工智能"
        assert node.trend_score == 0.8


class TestPersonNode:
    """PersonNode 模型测试"""

    def test_create_minimal(self):
        """测试 PersonNode 最小字段创建"""
        node = PersonNode(name="张三")
        assert node.name == "张三"
        assert node.skills == []
        assert node.experience_years == 0
        assert node.resume_hash == ""

    def test_create_full(self):
        """测试 PersonNode 全字段创建"""
        node = PersonNode(
            name="李四",
            skills=["Python", "Java"],
            experience_years=5,
            education="硕士",
            current_position="高级工程师",
            resume_hash="abc123",
        )
        assert len(node.skills) == 2
        assert node.experience_years == 5


class TestGraphTriple:
    """GraphTriple 模型测试"""

    def test_create_minimal(self):
        """测试 GraphTriple 最小字段创建"""
        triple = GraphTriple(
            head="Python",
            relation="similar_to",
            tail="Java",
        )
        assert triple.head == "Python"
        assert triple.relation == "similar_to"
        assert triple.tail == "Java"
        assert triple.confidence == 0.8
        assert isinstance(triple.properties, dict)
        assert isinstance(triple.timestamp, datetime)

    def test_create_full(self):
        """测试 GraphTriple 全字段创建"""
        triple = GraphTriple(
            head="Kubernetes",
            relation="requires",
            tail="Docker",
            confidence=0.95,
            source_id="src_001",
            evidence="岗位JD明确要求K8s和Docker",
            properties={"importance": "critical"},
        )
        assert triple.confidence == 0.95
        assert triple.source_id == "src_001"
        assert triple.properties["importance"] == "critical"

    def test_confidence_range(self):
        """测试 confidence 范围验证"""
        with pytest.raises(ValidationError):
            GraphTriple(
                head="A",
                relation="rel",
                tail="B",
                confidence=1.5,
            )

    def test_default_properties(self):
        """测试默认 properties 为空字典"""
        triple = GraphTriple(head="A", relation="rel", tail="B")
        assert triple.properties == {}
