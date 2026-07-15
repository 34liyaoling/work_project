"""技能标准化单元测试

覆盖：
- 别名 → 标准名映射
- 大小写不敏感
- 词典加载与查询
- 边界场景（空字符串、特殊字符、未知技能）
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest


# ============================================================
# 词典加载工具
# ============================================================
def _build_skill_normalizer(skills_data):
    """构造一个临时的技能标准化器（不依赖数据库）"""
    # 转换为 dict: alias -> standard_name
    alias_map = {}
    for item in skills_data:
        alias_map[item["alias"].lower()] = {
            "standard_name": item["standard_name"],
            "category": item.get("category", "未分类"),
        }
    return alias_map


def _normalize(skill_name: str, alias_map: dict):
    """根据 alias_map 进行技能标准化"""
    if not skill_name:
        return None
    key = skill_name.lower().strip()
    if key in alias_map:
        return alias_map[key]
    # 自身即为标准名
    for v in alias_map.values():
        if v["standard_name"].lower() == key:
            return v
    return None


# ============================================================
# 测试数据
# ============================================================
@pytest.fixture
def sample_skill_dict():
    """示例技能词典（与 data/skill_dictionary.json 格式一致）"""
    return [
        {"alias": "ML", "standard_name": "机器学习", "category": "AI"},
        {"alias": "机器学习", "standard_name": "机器学习", "category": "AI"},
        {"alias": "Machine Learning", "standard_name": "机器学习", "category": "AI"},
        {"alias": "DL", "standard_name": "深度学习", "category": "AI"},
        {"alias": "深度学习", "standard_name": "深度学习", "category": "AI"},
        {"alias": "Python", "standard_name": "Python", "category": "编程语言"},
        {"alias": "python", "standard_name": "Python", "category": "编程语言"},
        {"alias": "PYTHON", "standard_name": "Python", "category": "编程语言"},
        {"alias": "Vue", "standard_name": "Vue", "category": "前端框架"},
        {"alias": "vue.js", "standard_name": "Vue", "category": "前端框架"},
    ]


@pytest.fixture
def normalizer(sample_skill_dict):
    """构造标准化器"""
    return _build_skill_normalizer(sample_skill_dict)


# ============================================================
# 别名映射
# ============================================================
def test_alias_to_standard_name(normalizer):
    """别名应能正确映射到标准名"""
    result = _normalize("ML", normalizer)
    assert result is not None
    assert result["standard_name"] == "机器学习"
    assert result["category"] == "AI"


def test_multiple_aliases_same_standard(normalizer):
    """同一标准名的多个别名均应能识别"""
    for alias in ["ML", "机器学习", "Machine Learning"]:
        result = _normalize(alias, normalizer)
        assert result is not None
        assert result["standard_name"] == "机器学习"


def test_chinese_alias_works(normalizer):
    """中文别名直接命中"""
    result = _normalize("深度学习", normalizer)
    assert result["standard_name"] == "深度学习"


def test_english_abbreviation_works(normalizer):
    """英文缩写命中"""
    result = _normalize("DL", normalizer)
    assert result["standard_name"] == "深度学习"


# ============================================================
# 大小写不敏感
# ============================================================
@pytest.mark.parametrize("alias,expected", [
    ("python", "Python"),
    ("PYTHON", "Python"),
    ("Python", "Python"),
    ("pyThOn", "Python"),
])
def test_case_insensitive(normalizer, alias, expected):
    """查找应大小写不敏感"""
    result = _normalize(alias, normalizer)
    assert result is not None
    assert result["standard_name"] == expected


# ============================================================
# 边界场景
# ============================================================
def test_empty_string_returns_none(normalizer):
    """空字符串返回 None"""
    assert _normalize("", normalizer) is None


def test_unknown_skill_returns_none(normalizer):
    """未知技能返回 None"""
    assert _normalize("不存在的技能XYZ", normalizer) is None


def test_whitespace_trimmed(normalizer):
    """前后空格应被去除"""
    result = _normalize("  Python  ", normalizer)
    assert result is not None
    assert result["standard_name"] == "Python"


def test_standard_name_itself_resolves(normalizer):
    """传入标准名本身也应能解析"""
    result = _normalize("Python", normalizer)
    assert result is not None


def test_dot_in_name(normalizer):
    """带点的名称（如 vue.js）能识别"""
    result = _normalize("vue.js", normalizer)
    assert result is not None
    assert result["standard_name"] == "Vue"


# ============================================================
# 词典文件加载
# ============================================================
def test_load_real_skill_dictionary():
    """加载真实的 skill_dictionary.json（项目自带）"""
    dict_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "skill_dictionary.json"
    )
    if not os.path.exists(dict_path):
        pytest.skip(f"技能词典不存在: {dict_path}")

    with open(dict_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert len(data) > 50, "词典条目应丰富"

    # 校验结构
    for item in data:
        assert "alias" in item
        assert "standard_name" in item

    # 用真实数据构造 normalizer
    normalizer = _build_skill_normalizer(data)

    # 抽样验证
    r1 = _normalize("ML", normalizer)
    assert r1 is not None
    assert r1["standard_name"] == "机器学习"

    r2 = _normalize("tf", normalizer) or _normalize("TensorFlow", normalizer)
    assert r2 is not None
    assert r2["standard_name"] == "TensorFlow"


def test_normalize_does_not_mutate_input(normalizer):
    """标准化过程不应修改原字符串"""
    s = "  Python  "
    original = s
    _normalize(s, normalizer)
    assert s == original  # 字符串不可变，但确认无副作用


# ============================================================
# 批量标准化
# ============================================================
def test_batch_normalize_returns_unique_standards(normalizer):
    """批量标准化时应返回去重的标准名集合"""
    raw_skills = ["ML", "机器学习", "Python", "python", "未知技能"]
    standards = set()
    for s in raw_skills:
        r = _normalize(s, normalizer)
        if r:
            standards.add(r["standard_name"])
    assert "机器学习" in standards
    assert "Python" in standards
    # ML 和 机器学习 应合并为同一标准名
    assert len(standards) == 2


def test_normalize_preserves_category_info(normalizer):
    """标准化结果应保留分类信息"""
    r = _normalize("ML", normalizer)
    assert r["category"] == "AI"

    r2 = _normalize("Python", normalizer)
    assert r2["category"] == "编程语言"


# ============================================================
# 性能与稳定性
# ============================================================
def test_normalize_performance_with_large_dict():
    """大数据词典下响应应 < 100ms"""
    import time
    # 构造 5000 条词典
    data = [
        {"alias": f"skill_{i}", "standard_name": f"Standard_{i % 500}", "category": f"cat_{i % 10}"}
        for i in range(5000)
    ]
    normalizer = _build_skill_normalizer(data)
    start = time.time()
    for _ in range(1000):
        _normalize("skill_250", normalizer)
    elapsed = time.time() - start
    assert elapsed < 1.0, f"1000 次查询耗时 {elapsed:.3f}s 过长"
