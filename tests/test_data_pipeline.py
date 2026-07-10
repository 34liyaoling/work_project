"""数据管道测试 - DataPipeline"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from models.job_model import JobPostSource, JobPostRaw
from core.data_pipeline import DataPipeline


class TestComputeCompleteness:
    """compute_completeness 功能测试"""

    def test_empty_record(self):
        """测试空记录完整度为0"""
        pipeline = DataPipeline()
        record = JobPostRaw(source=JobPostSource.MANUAL, raw_content="")
        completeness = pipeline._calculate_completeness(record)
        assert completeness == 0.0

    def test_full_record(self):
        """测试完整记录"""
        pipeline = DataPipeline()
        record = JobPostRaw(
            source=JobPostSource.MANUAL,
            raw_content="test",
            job_title="测试岗位",
            company_name="测试公司",
            skills=["Python"],
            salary_min=20,
            location="北京",
            experience_min=2,
            education="本科",
        )
        completeness = pipeline._calculate_completeness(record)
        assert completeness > 0.5
        assert completeness <= 1.0

    def test_partial_record(self):
        """测试部分填充的记录"""
        pipeline = DataPipeline()
        record = JobPostRaw(
            source=JobPostSource.MANUAL,
            raw_content="",
            job_title="测试岗位",
            skills=["Python"],
        )
        completeness = pipeline._calculate_completeness(record)
        assert 0 < completeness < 0.5

    def test_only_source(self):
        """测试只有来源字段"""
        pipeline = DataPipeline()
        record = JobPostRaw(source=JobPostSource.MANUAL, raw_content="")
        completeness = pipeline._calculate_completeness(record)
        assert completeness == 0.0


class TestDeduplicate:
    """deduplicate 功能测试"""

    def test_exact_duplicate(self):
        """测试精确去重"""
        pipeline = DataPipeline()
        now = datetime.now()
        records = [
            JobPostRaw(source=JobPostSource.MANUAL, timestamp=now, raw_content="",
                       job_title="Python开发工程师", skills=["Python"]),
            JobPostRaw(source=JobPostSource.MANUAL, timestamp=now, raw_content="",
                       job_title="Python开发工程师", skills=["Python", "Django"]),
            JobPostRaw(source=JobPostSource.MANUAL, timestamp=now, raw_content="",
                       job_title="Java开发工程师", skills=["Java"]),
        ]
        unique = pipeline.deduplicate(records)
        assert len(unique) == 2
        titles = [r.job_title for r in unique]
        assert "Java开发工程师" in titles

    def test_no_duplicates(self):
        """测试无重复"""
        pipeline = DataPipeline()
        now = datetime.now()
        records = [
            JobPostRaw(source=JobPostSource.MANUAL, timestamp=now, raw_content="",
                       job_title="Python开发", skills=["Python"]),
            JobPostRaw(source=JobPostSource.MANUAL, timestamp=now, raw_content="",
                       job_title="Java开发", skills=["Java"]),
            JobPostRaw(source=JobPostSource.MANUAL, timestamp=now, raw_content="",
                       job_title="Go开发", skills=["Go"]),
        ]
        unique = pipeline.deduplicate(records)
        assert len(unique) == 3

    def test_substring_duplicate(self):
        """测试子串模糊匹配去重"""
        pipeline = DataPipeline()
        now = datetime.now()
        records = [
            JobPostRaw(source=JobPostSource.MANUAL, timestamp=now, raw_content="",
                       job_title="高级Python开发工程师", skills=["Python"]),
            JobPostRaw(source=JobPostSource.MANUAL, timestamp=now, raw_content="",
                       job_title="Python开发工程师", skills=["Python"]),
        ]
        unique = pipeline.deduplicate(records)
        assert len(unique) == 1

    def test_empty_title(self):
        """测试空标题记录被跳过"""
        pipeline = DataPipeline()
        now = datetime.now()
        records = [
            JobPostRaw(source=JobPostSource.MANUAL, timestamp=now, raw_content="",
                       job_title="", skills=["Python"]),
            JobPostRaw(source=JobPostSource.MANUAL, timestamp=now, raw_content="",
                       job_title="Python开发", skills=["Python"]),
        ]
        unique = pipeline.deduplicate(records)
        assert len(unique) == 1


class TestComputeFreshness:
    """compute_freshness 功能测试"""

    def test_fresh_record(self):
        """测试新鲜记录"""
        pipeline = DataPipeline()
        fresh = JobPostRaw(source=JobPostSource.MANUAL, timestamp=datetime.now(), raw_content="")
        assert pipeline._calculate_freshness(fresh) > 0.9

    def test_old_record(self):
        """测试陈旧记录"""
        pipeline = DataPipeline()
        old = JobPostRaw(source=JobPostSource.MANUAL, timestamp=datetime.now() - timedelta(days=60), raw_content="")
        assert pipeline._calculate_freshness(old) < 0.5

    def test_very_old_record(self):
        """测试极旧的记录新鲜度为0"""
        pipeline = DataPipeline()
        very_old = JobPostRaw(source=JobPostSource.MANUAL,
                              timestamp=datetime.now() - timedelta(days=365), raw_content="")
        freshness = pipeline._calculate_freshness(very_old)
        assert freshness == 0.0

    def test_recent_week(self):
        """测试一周内的记录高新鲜度"""
        pipeline = DataPipeline()
        recent = JobPostRaw(source=JobPostSource.MANUAL,
                            timestamp=datetime.now() - timedelta(days=3), raw_content="")
        assert pipeline._calculate_freshness(recent) > 0.85


class TestProcessRawData:
    """process_raw_data 功能测试"""

    def test_process_full(self):
        """测试完整数据处理"""
        pipeline = DataPipeline()
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

    def test_process_minimal(self):
        """测试最小数据处理"""
        pipeline = DataPipeline()
        raw = {"jobTitle": "测试"}
        processed = pipeline.process_raw_data(raw, JobPostSource.MANUAL)
        assert processed.job_title == "测试"
        assert processed.freshness_score > 0

    def test_process_with_different_keys(self):
        """测试不同字段名映射"""
        pipeline = DataPipeline()
        raw = {
            "position": "后端工程师",
            "brandName": "阿里巴巴",
            "minSalary": 30,
            "workCity": "杭州",
        }
        processed = pipeline.process_raw_data(raw, JobPostSource.LAGOU)
        assert processed.job_title == "后端工程师"
        assert processed.company_name == "阿里巴巴"
        assert processed.salary_min == 30
        assert processed.location == "杭州"

    def test_source_confidence_mapping(self):
        """测试数据源置信度映射"""
        pipeline = DataPipeline()
        raw = {"jobTitle": "测试"}

        sample = pipeline.process_raw_data(raw, JobPostSource.SAMPLE)
        assert sample.source_confidence == 1.0

        web = pipeline.process_raw_data(raw, JobPostSource.WEB_SEARCH)
        assert web.source_confidence == 0.6


class TestExtractSkillsFromJD:
    """技能提取测试"""

    def test_extract_from_description(self):
        """测试从JD描述中提取技能"""
        pipeline = DataPipeline()
        raw = {
            "jobTitle": "AI工程师",
            "description": "需要熟练掌握Python和机器学习，熟悉PyTorch框架",
        }
        skills = pipeline._extract_skills_from_raw(raw)
        assert "Python" in skills
        assert "PyTorch" in skills or "机器学习" in skills

    def test_extract_from_skills_field(self):
        """测试从skills字段提取"""
        pipeline = DataPipeline()
        raw = {
            "jobTitle": "测试",
            "skills": ["Python", "Java", "Go"],
        }
        skills = pipeline._extract_skills_from_raw(raw)
        assert "Python" in skills
        assert "Java" in skills
        assert len(skills) == 3

    def test_extract_empty(self):
        """测试空数据返回空列表"""
        pipeline = DataPipeline()
        raw = {"jobTitle": "测试"}
        skills = pipeline._extract_skills_from_raw(raw)
        assert skills == []


class TestRecordHash:
    """record_hash 功能测试"""

    def test_same_data_same_hash(self):
        """测试相同数据产生相同哈希"""
        pipeline = DataPipeline()
        data1 = {"title": "test", "skills": ["Python"]}
        data2 = {"title": "test", "skills": ["Python"]}
        assert pipeline.compute_record_hash(data1) == pipeline.compute_record_hash(data2)

    def test_different_data_different_hash(self):
        """测试不同数据产生不同哈希"""
        pipeline = DataPipeline()
        data1 = {"title": "test", "skills": ["Python"]}
        data2 = {"title": "test", "skills": ["Java"]}
        assert pipeline.compute_record_hash(data1) != pipeline.compute_record_hash(data2)

    def test_hash_is_string(self):
        """测试哈希返回字符串"""
        pipeline = DataPipeline()
        h = pipeline.compute_record_hash({"key": "value"})
        assert isinstance(h, str)
        assert len(h) > 0


class TestCleanData:
    """数据清洗测试"""

    def test_clean_whitespace(self):
        """测试清理字符串字段空格"""
        pipeline = DataPipeline()
        record = JobPostRaw(
            source=JobPostSource.MANUAL,
            raw_content="",
            job_title="  全栈  工程师  ",
        )
        pipeline._clean_data(record)
        assert record.job_title == "全栈 工程师"

    def test_clean_salary_conversion(self):
        """测试薪资字段转换"""
        pipeline = DataPipeline()
        record = JobPostRaw(
            source=JobPostSource.MANUAL,
            raw_content="",
            salary_min=30,
            salary_max=50,
        )
        pipeline._clean_data(record)
        assert record.salary_min == 30
        assert record.salary_max == 50

    def test_deduplicate_skills(self):
        """测试技能去重（大小写不敏感）"""
        pipeline = DataPipeline()
        record = JobPostRaw(
            source=JobPostSource.MANUAL,
            raw_content="",
            skills=["Python", "python", "PYTHON", "Java"],
        )
        pipeline._clean_data(record)
        assert len(record.skills) == 2

    def test_clean_no_salary(self):
        """测试无薪资字段处理"""
        pipeline = DataPipeline()
        record = JobPostRaw(
            source=JobPostSource.MANUAL,
            raw_content="",
            job_title="测试岗位",
            skills=["Python"],
        )
        pipeline._clean_data(record)
        assert record.job_title is not None


class TestProcessBatch:
    """批量处理测试"""

    def test_batch_processing(self):
        """测试批量处理"""
        pipeline = DataPipeline()
        items = [
            {"jobTitle": "岗位A", "skills": ["Python"]},
            {"jobTitle": "岗位B", "skills": ["Java"]},
        ]
        results = pipeline.process_batch(items, JobPostSource.MANUAL)
        assert len(results) == 2
        assert results[0].job_title == "岗位A"
        assert results[1].job_title == "岗位B"

    def test_batch_with_errors(self):
        """测试批量处理中的错误处理"""
        pipeline = DataPipeline()
        items = [
            {"jobTitle": "岗位A"},
            {},  # 空数据
            {"jobTitle": "岗位B"},
        ]
        results = pipeline.process_batch(items, JobPostSource.MANUAL)
        assert len(results) >= 2


class TestGetStats:
    """处理统计测试"""

    def test_stats_after_processing(self):
        """测试处理后统计信息"""
        pipeline = DataPipeline()
        raw = {"jobTitle": "测试岗位"}
        pipeline.process_raw_data(raw, JobPostSource.MANUAL)
        stats = pipeline.get_stats()
        assert stats["total_input"] == 1
        assert stats["processed"] == 1
        assert stats["errors"] == 0
