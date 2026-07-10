"""交叉验证引擎测试 - CrossValidator"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from models.job_model import JobPostRaw, JobPostSource
from core.cross_validator import CrossValidator, AgreementLevel


def make_record(job_title, source, skills=None, completeness=0.8, freshness=0.9,
                salary_min=None, salary_max=None, experience_min=None):
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
        salary_min=salary_min,
        salary_max=salary_max,
        experience_min=experience_min,
    )


class TestAgreementLevel:
    """一致性级别测试"""

    def test_three_source_agree(self):
        """测试3源一致 - 三个不同来源，高技能重叠"""
        validator = CrossValidator()

        r1 = make_record("AI工程师", "boss_zhipin", skills=["Python", "PyTorch", "机器学习"])
        r2 = make_record("AI工程师", "lagou", skills=["Python", "PyTorch", "深度学习"])
        r3 = make_record("AI工程师", "liepin", skills=["Python", "PyTorch", "机器学习"])

        for r in [r1, r2, r3]:
            validator.add_record(r)

        result = validator.validate_job("AI工程师")
        assert result["source_count"] >= 3
        assert result["agreement_level"] in [
            AgreementLevel.THREE_SOURCE_AGREE,
            AgreementLevel.TWO_SOURCE_AGREE,
        ]
        assert result["confidence"] > 0.5

    def test_two_source_agree(self):
        """测试2源一致"""
        validator = CrossValidator()

        r1 = make_record("数据分析师", "boss_zhipin", skills=["SQL", "Python"])
        r2 = make_record("数据分析师", "lagou", skills=["SQL", "Python", "Tableau"])

        for r in [r1, r2]:
            validator.add_record(r)

        result = validator.validate_job("数据分析师")
        assert result["source_count"] == 2
        assert result["agreement_level"] == AgreementLevel.TWO_SOURCE_AGREE
        assert result["confidence"] > 0.5

    def test_single_source(self):
        """测试单源"""
        validator = CrossValidator()
        r = make_record("Java开发", "manual", skills=["Java", "Spring"])
        validator.add_record(r)

        result = validator.validate_job("Java开发")
        assert result["source_count"] == 1
        assert result["agreement_level"] == AgreementLevel.SINGLE_SOURCE

    def test_conflict_detection(self):
        """测试冲突检测 - 薪资差异过大"""
        validator = CrossValidator()

        r1 = make_record("Java开发", "boss_zhipin", salary_min=10, salary_max=20)
        r2 = make_record("Java开发", "lagou", salary_min=50, salary_max=100)

        for r in [r1, r2]:
            validator.add_record(r)

        result = validator.validate_job("Java开发")
        if result["source_count"] >= 2:
            assert len(result["conflicts"]) > 0


class TestConfidenceCalculation:
    """置信度计算测试"""

    def test_high_confidence_three_source(self):
        """测试3源高置信度"""
        validator = CrossValidator()

        r1 = make_record("AI", "boss_zhipin", completeness=0.9, freshness=0.9)
        r2 = make_record("AI", "lagou", completeness=0.85, freshness=0.8)
        r3 = make_record("AI", "liepin", completeness=0.8, freshness=0.85)

        for r in [r1, r2, r3]:
            validator.add_record(r)

        result = validator.validate_job("AI")
        assert result["confidence"] > 0.5

    def test_low_quality_lowers_confidence(self):
        """测试低质量数据降低置信度"""
        validator = CrossValidator()

        r1 = make_record("岗位", "boss_zhipin", completeness=0.3, freshness=0.2)
        r2 = make_record("岗位", "lagou", completeness=0.2, freshness=0.1)

        for r in [r1, r2]:
            validator.add_record(r)

        result = validator.validate_job("岗位")
        assert result["confidence"] < 0.8

    def test_confidence_bounds(self):
        """测试置信度在0-1之间"""
        validator = CrossValidator()

        r1 = make_record("测试", "boss_zhipin", completeness=0.1, freshness=0.1)
        validator.add_record(r1)

        result = validator.validate_job("测试")
        assert 0 <= result["confidence"] <= 1.0


class TestFreshnessFactor:
    """新鲜度因子测试"""

    def test_fresh_records(self):
        """测试新鲜记录"""
        validator = CrossValidator()
        fresh = JobPostRaw(
            source=JobPostSource.MANUAL,
            source_confidence=0.9,
            timestamp=datetime.now(),
            job_title="测试岗位",
            skills=["Python"],
            completeness_score=0.8,
            freshness_score=1.0,
        )
        validator.add_record(fresh)
        result = validator.validate_job("测试岗位")
        assert result["confidence"] > 0.3

    def test_old_records(self):
        """测试陈旧记录"""
        validator = CrossValidator()
        old = JobPostRaw(
            source=JobPostSource.REPORT,
            source_confidence=0.8,
            timestamp=datetime.now() - timedelta(days=20),
            job_title="测试岗位",
            skills=["Python"],
            completeness_score=0.8,
            freshness_score=0.3,
        )
        validator.add_record(old)
        result = validator.validate_job("测试岗位")
        assert 0 < result["confidence"] <= 1.0
        assert result["validated_data"]["latest_update"] is not None


class TestWeightedAvg:
    """加权平均测试"""

    def test_basic(self):
        """测试基本加权平均"""
        validator = CrossValidator()
        values = [10, 20, 30]
        weights = [1, 2, 3]
        result = validator._weighted_avg(values, weights)
        expected = (10*1 + 20*2 + 30*3) / (1+2+3)
        assert abs(result - expected) < 0.001

    def test_equal_weights(self):
        """测试等权重"""
        validator = CrossValidator()
        result = validator._weighted_avg([10, 20, 30], [1, 1, 1])
        expected = (10 + 20 + 30) / 3
        assert abs(result - expected) < 0.001

    def test_empty_values(self):
        """测试空列表"""
        validator = CrossValidator()
        result = validator._weighted_avg([], [])
        assert result == 0

    def test_zero_weights(self):
        """测试零权重"""
        validator = CrossValidator()
        result = validator._weighted_avg([10, 20], [0, 0])
        expected = (10 + 20) / 2
        assert abs(result - expected) < 0.001


class TestValidateAll:
    """批量验证测试"""

    def test_validate_all(self):
        """测试验证所有已聚类数据"""
        validator = CrossValidator()

        r1 = make_record("AI", "boss_zhipin")
        r2 = make_record("Java", "lagou")
        r3 = make_record("AI", "liepin")

        for r in [r1, r2, r3]:
            validator.add_record(r)

        results = validator.validate_all()
        assert len(results) == 2
        assert results[0]["confidence"] >= results[1]["confidence"]

    def test_validate_all_empty(self):
        """测试空数据"""
        validator = CrossValidator()
        results = validator.validate_all()
        assert results == []


class TestAddBatch:
    """批量添加测试"""

    def test_add_batch(self):
        """测试批量添加记录"""
        validator = CrossValidator()
        records = [
            make_record("AI", "boss_zhipin"),
            make_record("Java", "lagou"),
        ]
        validator.add_batch(records)
        assert len(validator._job_clusters) == 2


class TestWarnings:
    """警告测试"""

    def test_data_volume_warning(self):
        """测试数据量不足警告"""
        validator = CrossValidator()
        r = make_record("AI", "boss_zhipin")
        validator.add_record(r)
        result = validator.validate_job("AI")
        has_volume_warning = any("数据量较少" in w for w in result["warnings"])
        assert has_volume_warning

    def test_single_source_warning(self):
        """测试单一来源警告"""
        validator = CrossValidator()
        r = make_record("AI", "boss_zhipin")
        validator.add_record(r)
        result = validator.validate_job("AI")
        has_single_warning = any("单一数据源" in w for w in result["warnings"])
        assert has_single_warning

    def test_low_completeness_warning(self):
        """测试低完整度警告"""
        validator = CrossValidator()
        r = make_record("AI", "boss_zhipin", completeness=0.3)
        validator.add_record(r)
        result = validator.validate_job("AI")
        has_completeness_warning = any("完整度" in w for w in result["warnings"])
        assert has_completeness_warning


class TestSourceConfidenceAdjustment:
    """数据源置信度调整测试"""

    def test_adjust_up(self):
        """测试上调置信度"""
        validator = CrossValidator()
        validator.adjust_source_confidence("boss_zhipin", 0.1)
        assert validator._source_dynamic_confidence.get("boss_zhipin", 0.7) > 0.8

    def test_adjust_down(self):
        """测试下调置信度"""
        validator = CrossValidator()
        validator.adjust_source_confidence("boss_zhipin", -0.2)
        assert validator._source_dynamic_confidence.get("boss_zhipin", 0.7) < 0.7

    def test_adjust_bounds(self):
        """测试调整边界"""
        validator = CrossValidator()
        validator.adjust_source_confidence("unknown_source", -1.0)
        assert validator._source_dynamic_confidence.get("unknown_source", 0.7) >= 0.1

        validator.adjust_source_confidence("unknown_source", 1.0)
        assert validator._source_dynamic_confidence.get("unknown_source", 0.7) <= 1.0


class TestValidationSummary:
    """验证摘要测试"""

    def test_summary(self):
        """测试验证摘要"""
        validator = CrossValidator()

        r1 = make_record("AI", "boss_zhipin")
        r2 = make_record("Java", "lagou")
        validator.add_batch([r1, r2])

        summary = validator.get_validation_summary()
        assert summary["total_clusters"] == 2
        assert summary["total_records"] == 2
        assert summary["validation_count"] == 0
