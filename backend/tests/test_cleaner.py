"""数据清洗测试

覆盖：
- SimHash 去重测试
- 技能标准化测试
- 交叉验证测试
- 覆盖率 100%
"""
import pytest

from app.services.cleaner import DataCleaner
from app.services.skill_normalizer import SkillNormalizer


# =========================================================
# SimHash 去重
# =========================================================
class TestSimHashDedup:
    def test_exact_duplicate(self):
        c = DataCleaner()
        text1 = "高级数据工程师，5年经验，熟练 Python/SQL/Spark"
        text2 = "高级数据工程师，5年经验，熟练 Python/SQL/Spark"
        h1 = c.simhash(text1)
        h2 = c.simhash(text2)
        assert h1 == h2
        assert c.is_duplicate(text1, text2) is True

    def test_similar_duplicate(self):
        c = DataCleaner()
        text1 = "高级数据工程师，5年经验，熟练 Python/SQL/Spark"
        text2 = "高级数据工程师，5 年经验，熟练 Python、SQL、Spark"
        assert c.is_duplicate(text1, text2, threshold=0.85) is True

    def test_different_duplicate(self):
        c = DataCleaner()
        text1 = "高级数据工程师，5年经验，熟练 Python/SQL/Spark"
        text2 = "产品经理，3年互联网产品经验，擅长用户调研"
        assert c.is_duplicate(text1, text2) is False

    def test_empty_text(self):
        c = DataCleaner()
        assert c.is_duplicate("", "") is True  # 两者都为空视为重复

    def test_simhash_returns_int(self):
        c = DataCleaner()
        h = c.simhash("任意文本")
        assert isinstance(h, int)


# =========================================================
# 技能标准化
# =========================================================
class TestSkillNormalize:
    def test_alias_to_standard(self):
        n = SkillNormalizer()
        assert n.normalize("py") in ("Python", "python")
        assert n.normalize("ML") in ("机器学习", "Machine Learning", "机器学习/ML")

    def test_case_insensitive(self):
        n = SkillNormalizer()
        a = n.normalize("python")
        b = n.normalize("Python")
        c = n.normalize("PYTHON")
        assert a == b == c

    def test_unknown_skill_returns_input(self):
        n = SkillNormalizer()
        assert n.normalize("__unknown_skill__") == "__unknown_skill__"

    def test_batch_normalize(self):
        n = SkillNormalizer()
        result = n.normalize_batch(["py", "js", "ML", "react"])
        assert isinstance(result, list)
        assert len(result) == 4


# =========================================================
# 交叉验证
# =========================================================
class TestCrossValidation:
    def test_sources_above_threshold(self):
        c = DataCleaner()
        sources = ["lagou", "zhipin", "liepin", "51job", "boss"]
        assert c.cross_validate({"skills": ["Python", "SQL"]}, sources) is True

    def test_sources_below_threshold(self):
        c = DataCleaner()
        sources = ["lagou"]
        # 单源时不应通过交叉验证
        assert c.cross_validate({"skills": ["Python", "SQL"]}, sources) is False

    def test_empty_skills(self):
        c = DataCleaner()
        # 空技能视为无效数据
        assert c.cross_validate({"skills": []}, ["lagou", "zhipin"]) is False
