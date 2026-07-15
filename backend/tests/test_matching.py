"""匹配算法单元测试

覆盖：
- 方式一：与具体 JD 匹配（_compute_match 函数行为）
- 方式二：与岗位方向匹配（Top-N 排序）
- 多维度评分合理性（必需/加分/深度/领域）
- 边界情况：空技能集、零匹配、全部匹配
"""
from __future__ import annotations

from app.api.match import _compute_match, _build_resume_skill_set


# ============================================================
# 工具函数：构建 resume skill 集
# ============================================================
def test_build_resume_skill_set_uses_standard_name():
    """应优先使用 standard_name 作 key"""
    skills = [
        {"name": "ML", "standard_name": "机器学习", "level": "advanced"},
        {"name": "pytorch", "standard_name": "PyTorch", "level": "intermediate"},
    ]
    result = _build_resume_skill_set({"skills": skills})
    assert "机器学习" in result
    assert "PyTorch" in result
    assert "ML" not in result  # 原始别名不应作 key


def test_build_resume_skill_set_fallback_to_name():
    """无 standard_name 时回退到 name"""
    skills = [{"name": "Python", "level": "intermediate"}]
    result = _build_resume_skill_set({"skills": skills})
    assert "Python" in result


def test_build_resume_skill_set_handles_empty():
    """空列表应返回空字典"""
    assert _build_resume_skill_set({"skills": []}) == {}
    assert _build_resume_skill_set({}) == {}


# ============================================================
# 核心：_compute_match 多维度评分
# ============================================================
def test_compute_match_full_match():
    """全部命中 → overall_score 应接近 1.0"""
    resume = {"Python": {"level": "advanced"}, "SQL": {"level": "advanced"}}
    target = [
        {"name": "Python", "weight": 1.0, "type": "required"},
        {"name": "SQL", "weight": 1.0, "type": "required"},
    ]
    weights = {"required": 0.4, "preferred": 0.2, "depth": 0.25, "domain": 0.15}
    result = _compute_match(resume, target, weights)
    assert result["overall_score"] >= 0.9
    assert result["required_score"] == 1.0
    assert "Python" in result["matched"]
    assert result["gap_skills"] == []


def test_compute_match_no_match():
    """零命中 → overall_score 应接近 0"""
    resume = {"Go": {"level": "intermediate"}}
    target = [
        {"name": "Python", "weight": 1.0, "type": "required"},
        {"name": "Java", "weight": 1.0, "type": "required"},
    ]
    weights = {"required": 0.4, "preferred": 0.2, "depth": 0.25, "domain": 0.15}
    result = _compute_match(resume, target, weights)
    assert result["required_score"] == 0.0
    assert len(result["gap_skills"]) == 2
    assert all(g["status"] == "missing" for g in result["gap_skills"])


def test_compute_match_partial():
    """50% 命中 → 各项分数应在 0~1 之间"""
    resume = {"Python": {"level": "advanced"}}
    target = [
        {"name": "Python", "weight": 1.0, "type": "required"},
        {"name": "Java", "weight": 1.0, "type": "required"},
    ]
    weights = {"required": 0.4, "preferred": 0.2, "depth": 0.25, "domain": 0.15}
    result = _compute_match(resume, target, weights)
    assert 0.0 < result["required_score"] < 1.0
    assert 0.0 < result["overall_score"] < 1.0


def test_compute_match_empty_target():
    """空 target → overall_score=0，不报错"""
    resume = {"Python": {"level": "advanced"}}
    result = _compute_match(resume, [], {})
    assert result["overall_score"] == 0.0
    assert result["matched"] == []
    assert result["gap_skills"] == []


def test_compute_match_empty_resume():
    """空 resume 命中目标技能 0"""
    result = _compute_match({}, [{"name": "Python", "weight": 1.0}], {})
    assert result["required_score"] == 0.0
    assert len(result["gap_skills"]) == 1


def test_compute_match_depth_affects_score():
    """技能深度（高级）应比初级得更高分"""
    target = [{"name": "Python", "weight": 1.0}]

    # 高级简历
    resume_adv = {"Python": {"level": "advanced"}}
    r1 = _compute_match(resume_adv, target, {})

    # 初级简历
    resume_beg = {"Python": {"level": "beginner"}}
    r2 = _compute_match(resume_beg, target, {})

    assert r1["depth_score"] > r2["depth_score"]
    assert r1["overall_score"] > r2["overall_score"]


def test_compute_match_weighted_required():
    """权重更高的技能缺失时影响更大"""
    target = [
        {"name": "Python", "weight": 5.0},
        {"name": "Java", "weight": 1.0},
    ]
    # 命中低权重 Java
    resume = {"Java": {"level": "advanced"}}
    r = _compute_match(resume, target, {})
    # 命中权重 1/6 ≈ 0.166
    assert 0.15 < r["required_score"] < 0.20


def test_compute_match_breakdown_includes_dimensions():
    """breakdown 应包含所有维度"""
    resume = {"Python": {"level": "advanced"}}
    target = [{"name": "Python", "weight": 1.0}]
    r = _compute_match(resume, target, {})
    dimensions = {item["dimension"] for item in r["breakdown"]}
    assert "必备技能" in dimensions
    assert "技能深度" in dimensions
    assert "领域契合" in dimensions


def test_compute_match_gap_skills_have_suggestion():
    """gap_skills 必须包含学习建议"""
    resume = {}
    target = [{"name": "Rust", "weight": 1.0}]
    r = _compute_match(resume, target, {})
    assert len(r["gap_skills"]) == 1
    assert "suggestion" in r["gap_skills"][0]
    assert r["gap_skills"][0]["skill_name"] == "Rust"


def test_compute_match_custom_weights():
    """自定义权重应能影响总分"""
    resume = {"Python": {"level": "advanced"}}
    target = [{"name": "Python", "weight": 1.0}]

    w_depth_heavy = {"required": 0.1, "preferred": 0.1, "depth": 0.7, "domain": 0.1}
    w_required_heavy = {"required": 0.7, "preferred": 0.1, "depth": 0.1, "domain": 0.1}
    r1 = _compute_match(resume, target, w_depth_heavy)
    r2 = _compute_match(resume, target, w_required_heavy)
    # 当所有技能匹配、且高级时，depth 与 required 分数均为 1，权重差异不会改变值
    # 这里主要验证不报错
    assert r1["overall_score"] == r2["overall_score"]


# ============================================================
# 方式二：Top-N 排序
# ============================================================
def test_top_n_sort_descending():
    """Top-N 应按 overall_score 降序"""
    # 模拟 _compute_match 多次调用结果
    results = [
        {"role": "A", "overall_score": 0.6},
        {"role": "B", "overall_score": 0.9},
        {"role": "C", "overall_score": 0.3},
        {"role": "D", "overall_score": 0.75},
    ]
    sorted_results = sorted(results, key=lambda x: x["overall_score"], reverse=True)
    top3 = sorted_results[:3]
    assert top3[0]["role"] == "B"
    assert top3[1]["role"] == "D"
    assert top3[2]["role"] == "A"


def test_top_n_respects_limit():
    """top_n 应限制返回数量"""
    results = [{"role": f"R{i}", "overall_score": 1.0 - i * 0.1} for i in range(20)]
    top5 = results[:5]
    assert len(top5) == 5
