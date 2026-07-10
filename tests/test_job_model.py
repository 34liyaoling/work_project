"""岗位模型测试 - JobPostRaw、JobPostSource、JobDiscoveryCandidate"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from models.job_model import JobPostSource, JobPostRaw, JobDiscoveryCandidate, JobMarketIntelligence


class TestJobPostSource:
    """JobPostSource 枚举测试"""

    def test_values(self):
        """测试 JobPostSource 枚举值"""
        assert JobPostSource.BOSS_ZHIPIN.value == "boss_zhipin"
        assert JobPostSource.LAGOU.value == "lagou"
        assert JobPostSource.LIEPIN.value == "liepin"
        assert JobPostSource.ZHAOPIN.value == "zhaopin"
        assert JobPostSource.GITHUB.value == "github"
        assert JobPostSource.REPORT.value == "report"
        assert JobPostSource.MANUAL.value == "manual"
        assert JobPostSource.SAMPLE.value == "sample"
        assert JobPostSource.WEB_SEARCH.value == "web_search"

    def test_count(self):
        """测试枚举数量"""
        assert len(list(JobPostSource)) == 9

    def test_all_members(self):
        """测试所有成员"""
        members = {
            JobPostSource.BOSS_ZHIPIN,
            JobPostSource.LAGOU,
            JobPostSource.LIEPIN,
            JobPostSource.ZHAOPIN,
            JobPostSource.GITHUB,
            JobPostSource.REPORT,
            JobPostSource.MANUAL,
            JobPostSource.SAMPLE,
            JobPostSource.WEB_SEARCH,
        }
        assert set(JobPostSource) == members


class TestJobPostRaw:
    """JobPostRaw 模型测试"""

    def test_create_minimal(self):
        """测试最小字段创建"""
        now = datetime.now()
        record = JobPostRaw(
            source=JobPostSource.MANUAL,
            timestamp=now,
        )
        assert record.source == JobPostSource.MANUAL
        assert record.timestamp == now
        assert record.raw_content == ""
        assert record.job_title is None
        assert record.skills == []
        assert record.completeness_score == 0.0
        assert record.freshness_score == 1.0

    def test_create_full(self):
        """测试全字段创建"""
        now = datetime.now()
        record = JobPostRaw(
            source=JobPostSource.BOSS_ZHIPIN,
            source_confidence=0.85,
            timestamp=now,
            raw_content='{"jobTitle": "AI工程师"}',
            job_title="AI工程师",
            company_name="字节跳动",
            skills=["Python", "PyTorch", "机器学习"],
            salary_min=30,
            salary_max=80,
            location="北京",
            experience_min=3,
            experience_max=5,
            education="硕士",
            industry="互联网",
            company_size="10000+",
            job_description="负责AI算法研发",
            completeness_score=0.9,
            freshness_score=0.95,
        )
        assert record.source.value == "boss_zhipin"
        assert record.salary_min == 30
        assert record.salary_max == 80
        assert record.experience_min == 3
        assert record.completeness_score == 0.9

    def test_source_confidence_default(self):
        """测试 source_confidence 默认值"""
        record = JobPostRaw(source=JobPostSource.MANUAL, raw_content="")
        assert record.source_confidence == 0.8

    def test_timestamp_default(self):
        """测试 timestamp 默认值"""
        record = JobPostRaw(source=JobPostSource.MANUAL, raw_content="")
        assert isinstance(record.timestamp, datetime)

    def test_all_sources(self):
        """测试所有来源类型"""
        for source in JobPostSource:
            record = JobPostRaw(source=source, raw_content="")
            assert record.source == source

    def test_skills_default_empty_list(self):
        """测试 skills 默认空列表"""
        record = JobPostRaw(source=JobPostSource.MANUAL, raw_content="")
        assert record.skills == []

    def test_lagou_source(self):
        """测试拉勾来源创建"""
        record = JobPostRaw(
            source=JobPostSource.LAGOU,
            raw_content="",
            job_title="Java开发",
            company_name="美团",
        )
        assert record.source == JobPostSource.LAGOU


class TestJobDiscoveryCandidate:
    """JobDiscoveryCandidate 模型测试"""

    def test_create_minimal(self):
        """测试最小字段创建"""
        candidate = JobDiscoveryCandidate(
            suggested_title="AI训练师",
            skill_cluster=["Python", "数据标注"],
            confidence=0.85,
        )
        assert candidate.suggested_title == "AI训练师"
        assert len(candidate.skill_cluster) == 2
        assert candidate.confidence == 0.85
        assert candidate.growth_rate == 0.0
        assert candidate.discovery_reason == ""
        assert isinstance(candidate.timestamp, datetime)

    def test_create_full(self):
        """测试全字段创建"""
        candidate = JobDiscoveryCandidate(
            suggested_title="提示词工程师",
            skill_cluster=["Prompt Engineering", "LLM", "RAG"],
            confidence=0.92,
            evidence_sources=["Boss直聘", "猎聘"],
            growth_rate=0.35,
            similar_existing_jobs=["AI算法工程师"],
            suggested_definition={"required_skills": ["Python", "LangChain"]},
            discovery_reason="大模型领域新兴岗位",
        )
        assert len(candidate.evidence_sources) == 2
        assert candidate.growth_rate == 0.35
        assert candidate.suggested_definition["required_skills"][0] == "Python"

    def test_growth_rate_default(self):
        """测试 growth_rate 默认值"""
        candidate = JobDiscoveryCandidate(
            suggested_title="Test",
            skill_cluster=["Skill"],
            confidence=0.5,
        )
        assert candidate.growth_rate == 0.0


class TestJobMarketIntelligence:
    """JobMarketIntelligence 模型测试"""

    def test_create_minimal(self):
        """测试最小字段创建"""
        mi = JobMarketIntelligence(job_title="AI工程师")
        assert mi.job_title == "AI工程师"
        assert mi.total_openings == 0
        assert mi.competition_level == "medium"
        assert mi.top_skills == []
        assert mi.city_distribution == {}
        assert mi.demand_forecast == "stable"

    def test_create_full(self):
        """测试全字段创建"""
        mi = JobMarketIntelligence(
            job_title="AI工程师",
            total_openings=500,
            openings_change_30d=0.15,
            avg_salary_min=30,
            avg_salary_max=80,
            competition_level="high",
            top_companies=["字节跳动", "腾讯", "阿里巴巴"],
            top_skills=[{"skill": "Python", "frequency": 0.9}],
            city_distribution={"北京": 200, "上海": 150},
            demand_forecast="rising",
        )
        assert mi.total_openings == 500
        assert len(mi.top_companies) == 3
        assert mi.demand_forecast == "rising"
