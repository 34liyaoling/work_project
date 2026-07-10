"""数据库模块测试 - SQLite持久化存储"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import pytest
import tempfile
from datetime import datetime


@pytest.fixture(autouse=True)
def reset_db_singleton():
    """每个测试前重置数据库单例"""
    import backend.storage.db as db_module
    db_module._db_instance = None


class TestDatabase:
    """测试SQLite数据库模块"""

    @pytest.fixture
    def db(self):
        from backend.storage.db import DatabaseManager
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        db_path = tmp.name
        manager = DatabaseManager(db_path)
        manager.init_db()
        yield manager
        os.unlink(db_path)

    def test_save_and_get_resume(self, db):
        """测试简历保存和读取"""
        resume_id = "test_resume_001"
        profile = {
            "name": "张三",
            "email": "zhangsan@example.com",
            "skills_with_credibility": [
                {"skill_name": "Python", "credibility_score": 0.9},
                {"skill_name": "PyTorch", "credibility_score": 0.85},
                {"skill_name": "机器学习", "credibility_score": 0.8},
            ],
            "overall_technical_level": "senior",
        }

        db.save_resume(resume_id, profile)

        loaded = db.get_resume(resume_id)
        assert loaded is not None
        assert loaded["name"] == "张三"
        assert len(loaded["skills_with_credibility"]) == 3

        loaded_skills = {s["skill_name"] for s in loaded["skills_with_credibility"]}
        assert "Python" in loaded_skills
        assert "PyTorch" in loaded_skills

    def test_get_resume_not_found(self, db):
        """测试获取不存在的简历"""
        result = db.get_resume("non_existent_id")
        assert result is None

    def test_update_resume(self, db):
        """测试更新简历"""
        resume_id = "test_resume_update"
        profile_v1 = {
            "name": "李四",
            "skills_with_credibility": [{"skill_name": "Java", "credibility_score": 0.7}],
            "overall_technical_level": "mid",
        }
        db.save_resume(resume_id, profile_v1)

        profile_v2 = {
            "name": "李四",
            "skills_with_credibility": [
                {"skill_name": "Java", "credibility_score": 0.9},
                {"skill_name": "Spring Boot", "credibility_score": 0.8},
            ],
            "overall_technical_level": "senior",
        }
        db.save_resume(resume_id, profile_v2)

        loaded = db.get_resume(resume_id)
        assert loaded is not None
        assert len(loaded["skills_with_credibility"]) == 2

    def test_list_resumes(self, db):
        """测试列出简历"""
        for i in range(5):
            db.save_resume(
                f"resume_{i}",
                {
                    "name": f"用户{i}",
                    "skills_with_credibility": [{"skill_name": "Python", "credibility_score": 0.8}],
                    "overall_technical_level": "mid",
                }
            )

        resumes = db.list_resumes(limit=10)
        assert len(resumes) == 5

        resumes_limited = db.list_resumes(limit=3)
        assert len(resumes_limited) == 3

    def test_delete_resume(self, db):
        """测试删除简历"""
        resume_id = "test_delete"
        db.save_resume(resume_id, {
            "name": "待删除",
            "skills_with_credibility": [],
            "overall_technical_level": "junior",
        })

        assert db.get_resume(resume_id) is not None

        deleted = db.delete_resume(resume_id)
        assert deleted is True

        assert db.get_resume(resume_id) is None

        not_found = db.delete_resume("non_existent")
        assert not_found is False

    def test_save_and_get_job(self, db):
        """测试保存和获取岗位"""
        job = {
            "title": "AI算法工程师",
            "domain": "人工智能",
            "required_skills": ["Python", "PyTorch", "机器学习"],
            "avg_salary_min": 30,
            "avg_salary_max": 80,
            "source": "test",
        }

        db.save_job(job)

        jobs = db.get_jobs(limit=10)
        assert len(jobs) >= 1
        assert jobs[0]["title"] == "AI算法工程师"
        assert jobs[0]["domain"] == "人工智能"

    def test_get_jobs_by_domain(self, db):
        """测试按领域获取岗位"""
        db.save_job({"title": "Python开发", "domain": "软件开发"})
        db.save_job({"title": "AI工程师", "domain": "人工智能"})
        db.save_job({"title": "Java开发", "domain": "软件开发"})

        ai_jobs = db.get_jobs(domain="人工智能")
        assert len(ai_jobs) == 1
        assert ai_jobs[0]["title"] == "AI工程师"

        dev_jobs = db.get_jobs(domain="软件开发")
        assert len(dev_jobs) == 2

    def test_get_db_stats(self, db):
        """测试数据库统计"""
        stats = db.get_db_stats()
        assert "resume_count" in stats
        assert "job_count" in stats
        assert "analysis_count" in stats
        assert "pending_audit_count" in stats
        assert "domain_distribution" in stats
        assert "db_size_bytes" in stats

        # 添加一些数据后验证统计
        db.save_resume("stats_test_1", {
            "name": "测试", "skills_with_credibility": [], "overall_technical_level": "mid",
        })
        db.save_job({"title": "测试岗位", "domain": "测试领域"})

        updated_stats = db.get_db_stats()
        assert updated_stats["resume_count"] >= 1
        assert updated_stats["job_count"] >= 1

    def test_audit_queue(self, db):
        """测试审核队列"""
        db.add_audit_item({
            "item_type": "new_job",
            "title": "待审核岗位",
            "skills": ["Python"],
        })

        pending = db.get_audit_queue(status="pending")
        assert len(pending) >= 1
        assert pending[0]["item_type"] == "new_job"

        db.update_audit_item(item_id=pending[0]["id"], status="approved", reviewer_note="审核通过")

        approved = db.get_audit_queue(status="approved")
        assert len(approved) >= 1

    def test_init_db_idempotent(self, db):
        """测试数据库初始化幂等性"""
        db.init_db()
        db.init_db()
        db.init_db()

        db.save_resume("idempotent_test", {
            "name": "幂等测试",
            "skills_with_credibility": [],
            "overall_technical_level": "junior",
        })
        assert db.get_resume("idempotent_test") is not None

    def test_get_db_singleton(self):
        """测试数据库单例"""
        from backend.storage.db import get_db
        import backend.storage.db as db_module

        db1 = get_db()
        db2 = get_db()
        assert db1 is db2

    def test_save_resume_with_empty_skills(self, db):
        """测试保存空技能列表的简历"""
        resume_id = "empty_skills"
        db.save_resume(resume_id, {
            "name": "无技能",
            "skills_with_credibility": [],
            "overall_technical_level": "junior",
        })
        loaded = db.get_resume(resume_id)
        assert loaded is not None
        assert loaded["name"] == "无技能"


if __name__ == "__main__":
    pytest.main([__file__])
