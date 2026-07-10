"""核心模块测试 - 交叉验证、匹配引擎、数据管道"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

from models.job_model import JobPostRaw, JobPostSource
from core.cross_validator import CrossValidator, AgreementLevel
from core.data_pipeline import DataPipeline
from core.match_engine import HybridMatchEngine, MatchResult


# ========== 交叉验证测试 ==========

class TestCrossValidator:
    """test_cross_validator.py 风格的交叉验证测试"""

    def make_record(self, job_title, source, skills=None, completeness=0.8, freshness=0.9):
        """辅助方法：快速创建测试记录"""
        if skills is None:
            skills = ["Python", "SQL"]
        now = datetime.now()
        return JobPostRaw(
            source=JobPostSource(source),
            source_confidence=0.8,
            timestamp=now,
            job_title=job_title,
            skills=skills,
            completeness_score=completeness,
            freshness_score=freshness,
        )

    def test_agreement_levels(self):
        """测试3源一致/2源一致/单源/冲突"""
        validator = CrossValidator()

        # 三源一致：三个不同来源，相同技能
        r1 = self.make_record("AI工程师", "boss_zhipin", skills=["Python", "PyTorch", "机器学习"])
        r2 = self.make_record("AI工程师", "lagou", skills=["Python", "PyTorch", "深度学习"])
        r3 = self.make_record("AI工程师", "liepin", skills=["Python", "PyTorch", "机器学习"])

        for r in [r1, r2, r3]:
            validator.add_record(r)

        result = validator.validate_job("AI工程师")
        assert result["source_count"] >= 3
        assert result["agreement_level"] in [AgreementLevel.THREE_SOURCE_AGREE, AgreementLevel.TWO_SOURCE_AGREE]
        assert result["confidence"] > 0.5

        # 单源：仅一个来源
        validator2 = CrossValidator()
        r4 = self.make_record("数据分析师", "manual", skills=["SQL", "Python", "Pandas"])
        validator2.add_record(r4)

        result2 = validator2.validate_job("数据分析师")
        assert result2["source_count"] == 1
        assert result2["agreement_level"] == AgreementLevel.SINGLE_SOURCE

        # 冲突检测：薪资差异过大
        validator3 = CrossValidator()
        r5 = self.make_record("Java开发", "boss_zhipin")
        r5.salary_min = 10
        r5.salary_max = 20
        r6 = self.make_record("Java开发", "lagou")
        r6.salary_min = 50
        r6.salary_max = 100
        for r in [r5, r6]:
            validator3.add_record(r)

        result3 = validator3.validate_job("Java开发")
        if result3["source_count"] >= 2:
            assert len(result3["conflicts"]) > 0

    def test_freshness_factor(self):
        """测试新鲜度因子计算"""
        now = datetime.now()
        old_time = now - timedelta(days=20)

        # 新鲜记录
        fresh_record = JobPostRaw(
            source=JobPostSource.MANUAL,
            source_confidence=0.9,
            timestamp=now,
            job_title="测试岗位",
            skills=["Python"],
            completeness_score=0.8,
            freshness_score=1.0,
        )

        # 陈旧记录
        old_record = JobPostRaw(
            source=JobPostSource.REPORT,
            source_confidence=0.8,
            timestamp=old_time,
            job_title="测试岗位",
            skills=["Python"],
            completeness_score=0.8,
            freshness_score=0.3,
        )

        validator = CrossValidator()
        validator.add_record(fresh_record)
        validator.add_record(old_record)
        result = validator.validate_job("测试岗位")

        assert 0 < result["confidence"] <= 1.0
        assert result["validated_data"]["latest_update"] is not None

    def test_weighted_avg(self):
        """测试加权平均"""
        validator = CrossValidator()
        values = [10, 20, 30]
        weights = [1, 2, 3]
        result = validator._weighted_avg(values, weights)
        expected = (10*1 + 20*2 + 30*3) / (1+2+3)
        assert abs(result - expected) < 0.001


# ========== 匹配引擎测试 ==========

class TestMatchEngine:
    """test_match_engine.py 风格的匹配引擎测试"""

    @pytest.fixture
    def engine(self):
        with patch('core.match_engine.get_llm_service') as mock_llm, \
             patch('core.match_engine.get_graph_service') as mock_graph, \
             patch('core.match_engine.get_vector_service') as mock_vec:
            mock_graph_instance = MagicMock()
            mock_graph_instance.is_connected = False
            mock_graph.return_value = mock_graph_instance

            mock_vec_instance = MagicMock()
            mock_vec_instance.is_connected = False
            mock_vec.return_value = mock_vec_instance

            yield HybridMatchEngine()

    def test_calculate_match_score(self, engine):
        """测试匹配度计算"""
        resume = {
            "skills": ["Python", "PyTorch", "机器学习", "深度学习", "SQL"],
            "skills_with_credibility": [
                {"skill_name": "Python", "credibility_score": 0.9},
                {"skill_name": "PyTorch", "credibility_score": 0.8},
                {"skill_name": "机器学习", "credibility_score": 0.85},
            ],
            "embedding": [0.1, 0.2, 0.3],
            "implicit_skills": ["NLP", "数据分析"],
        }
        job = {
            "title": "AI算法工程师",
            "required_skills": ["Python", "PyTorch", "机器学习", "TensorFlow"],
            "optional_skills": ["SQL", "Docker"],
            "embedding": [0.15, 0.25, 0.35],
        }

        result = engine.calculate_match(resume, job)
        assert isinstance(result, MatchResult)
        assert 0 <= result.score <= 1.0
        assert len(result.matched_skills) > 0
        assert "Python" in result.matched_skills
        assert result.job_title == "AI算法工程师"

    def test_skill_match(self, engine):
        """测试技能匹配"""
        resume_skills = {"Python", "Java", "SQL", "React"}
        required = {"Python", "Kubernetes", "React"}
        optional = {"Docker", "SQL"}

        resume_profile = {
            "skills": list(resume_skills),
            "skills_with_credibility": [
                {"skill_name": "Python", "credibility_score": 0.9},
                {"skill_name": "Java", "credibility_score": 0.8},
                {"skill_name": "SQL", "credibility_score": 0.85},
                {"skill_name": "React", "credibility_score": 0.75},
            ],
        }

        score, matched, missing_crit, missing_opt = engine._calc_skill_match(
            resume_skills, required, optional, resume_profile
        )

        assert 0 <= score <= 1.0
        assert "Python" in matched
        assert "React" in matched
        assert "Kubernetes" in missing_crit
        assert "Docker" in missing_opt

    def test_empty_skills(self, engine):
        """测试空技能列表"""
        resume = {
            "skills": [],
            "skills_with_credibility": [],
            "embedding": None,
            "implicit_skills": [],
        }
        job = {
            "title": "测试岗位",
            "required_skills": ["Python", "Java"],
            "optional_skills": [],
            "embedding": None,
        }

        result = engine.calculate_match(resume, job)
        assert result.score >= 0
        assert len(result.matched_skills) == 0
        assert len(result.missing_critical) == 2

    def test_batch_calculate(self, engine):
        """测试批量计算"""
        resume = {
            "skills": ["Python"],
            "skills_with_credibility": [{"skill_name": "Python", "credibility_score": 0.8}],
            "embedding": [0.1],
            "implicit_skills": [],
        }
        jobs = [
            {"title": "岗位A", "required_skills": ["Python"], "optional_skills": [], "embedding": [0.1]},
            {"title": "岗位B", "required_skills": ["Java"], "optional_skills": [], "embedding": [0.5]},
        ]

        results = engine.batch_calculate(resume, jobs)
        assert len(results) == 2
        assert results[0].score >= results[1].score

    def test_find_similar(self, engine):
        """测试相似技能查找"""
        skill_set = {"PyTorch", "Kubernetes", "JavaScript"}

        assert engine._find_similar("pytorch", skill_set) == "PyTorch"
        assert engine._find_similar("kubernetes", skill_set) == "Kubernetes"
        assert engine._find_similar("javascript", skill_set) == "JavaScript"
        assert engine._find_similar("rust", skill_set) is None

    def test_explanation_format(self, engine):
        """测试解释文本格式"""
        explanation = engine._generate_explanation(
            "测试岗位", 0.85,
            {"skill": 0.9, "graph": 0.7, "vector": 0.8, "trend": 0.6, "credibility": 0.9},
            ["Python", "Java"], ["Go"], ["Rust"]
        )
        assert "测试岗位" in explanation
        assert "85" in explanation or "0.85" in explanation
        assert "Python" in explanation


# ========== 数据管道测试 ==========

class TestDataPipeline:
    """test_data_pipeline.py 风格的数据管道测试"""

    @pytest.fixture
    def pipeline(self):
        return DataPipeline()

    def test_deduplicate(self, pipeline):
        """测试去重"""
        now = datetime.now()

        records = [
            JobPostRaw(
                source=JobPostSource.MANUAL, timestamp=now,
                job_title="Python开发工程师", skills=["Python"],
                completeness_score=0.8, freshness_score=0.9, raw_content="",
            ),
            JobPostRaw(
                source=JobPostSource.MANUAL, timestamp=now,
                job_title="Python开发工程师", skills=["Python", "Django"],
                completeness_score=0.8, freshness_score=0.9, raw_content="",
            ),
            JobPostRaw(
                source=JobPostSource.MANUAL, timestamp=now,
                job_title="Java开发工程师", skills=["Java"],
                completeness_score=0.8, freshness_score=0.9, raw_content="",
            ),
        ]

        unique = pipeline.deduplicate(records)
        assert len(unique) == 2

        titles = [r.job_title for r in unique]
        assert "Java开发工程师" in titles

    def test_completeness(self, pipeline):
        """测试完整度计算"""
        record = JobPostRaw(
            source=JobPostSource.MANUAL,
            timestamp=datetime.now(),
            raw_content='{"test": "data"}',
        )

        # 空记录：完整度应为0
        completeness = pipeline._calculate_completeness(record)
        assert completeness == 0.0

        # 完整记录
        record.job_title = "测试岗位"
        record.company_name = "测试公司"
        record.skills = ["Python"]
        record.salary_min = 20
        record.location = "北京"
        record.experience_min = 2
        record.education = "本科"

        completeness = pipeline._calculate_completeness(record)
        assert completeness > 0.5
        assert completeness <= 1.0

    def test_freshness(self, pipeline):
        """测试新鲜度计算"""
        now = datetime.now()

        fresh = JobPostRaw(source=JobPostSource.MANUAL, timestamp=now, raw_content="")
        assert pipeline._calculate_freshness(fresh) > 0.9

        old = JobPostRaw(source=JobPostSource.MANUAL, timestamp=now - timedelta(days=60), raw_content="")
        assert pipeline._calculate_freshness(old) < 0.5

    def test_process_raw_data(self, pipeline):
        """测试原始数据处理"""
        raw = {
            "jobTitle": "全栈工程师",
            "companyName": "字节跳动",
            "skills": ["Python", "React", "Vue"],
            "salaryMin": 25,
            "salaryMax": 55,
            "city": "北京",
        }

        processed = pipeline.process_raw_data(raw, JobPostSource.WEB_SEARCH)
        assert processed.job_title == "全栈工程师"
        assert processed.company_name == "字节跳动"
        assert len(processed.skills) >= 2
        assert processed.salary_min == 25
        assert processed.salary_max == 55
        assert processed.completeness_score > 0

    def test_extract_skills_from_jd(self, pipeline):
        """测试从JD文本提取技能"""
        raw = {
            "jobTitle": "测试",
            "description": "需要熟练掌握Python和机器学习技能，熟悉PyTorch框架",
        }
        skills = pipeline._extract_skills_from_raw(raw)
        assert "Python" in skills
        assert "PyTorch" in skills or "机器学习" in skills

    def test_record_hash(self, pipeline):
        """测试哈希计算"""
        data1 = {"title": "test", "skills": ["Python"]}
        data2 = {"title": "test", "skills": ["Python"]}
        data3 = {"title": "test", "skills": ["Java"]}

        assert pipeline.compute_record_hash(data1) == pipeline.compute_record_hash(data2)
        assert pipeline.compute_record_hash(data1) != pipeline.compute_record_hash(data3)

    def test_clean_data(self, pipeline):
        """测试数据清洗"""
        record = JobPostRaw(
            source=JobPostSource.MANUAL,
            timestamp=datetime.now(),
            raw_content="",
            job_title="  全栈  工程师  ",
            skills=["Python", "python", "PYTHON", "Java"],
        )

        pipeline._clean_data(record)
        assert record.job_title == "全栈 工程师"


if __name__ == "__main__":
    pytest.main([__file__])
