"""人岗匹配测试集与评估函数

提供 MatchTestCase 数据结构、build_match_test_set 构造覆盖两种
匹配方式（JD 与 Role）的样本，evaluate_matchers 计算评估指标。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from app.core.logger import log


@dataclass
class MatchTestCase:
    """匹配测试用例"""
    case_id: str
    user_skills: List[Dict[str, Any]] = field(default_factory=list)
    jd_record: Dict[str, Any] = field(default_factory=dict)
    role_cards: List[Dict[str, Any]] = field(default_factory=list)
    expected_jd_score: float = 0.0  # 期望的 JD 匹配分（0-1）
    expected_top_role: str = ""     # 期望的 Top-1 岗位名


def build_match_test_set() -> List[MatchTestCase]:
    """构造覆盖 JD 匹配 / Role Top-N 的样本集"""
    cases: List[MatchTestCase] = []

    # Case 1: 完全匹配的 JD
    jd1 = {
        "jd_id": "jd_1", "company": "Bytedance",
        "parsed_data": {
            "job_title": "AI 工程师",
            "category": "AI工程师",
            "level": "中级",
            "required_skills": [
                {"skill": "Python", "level": "熟练", "weight": 0.9},
                {"skill": "PyTorch", "level": "熟练", "weight": 0.8},
                {"skill": "LangChain", "level": "基础", "weight": 0.6},
            ],
            "preferred_skills": [
                {"skill": "Kubernetes", "level": "基础", "weight": 0.4},
            ],
        },
    }
    user1 = [
        {"skill": "Python", "level": "熟练", "weight": 0.9},
        {"skill": "PyTorch", "level": "熟练", "weight": 0.8},
        {"skill": "LangChain", "level": "熟练", "weight": 0.7},
        {"skill": "Kubernetes", "level": "基础", "weight": 0.5},
    ]
    cases.append(MatchTestCase(
        case_id="jd_perfect_1", user_skills=user1, jd_record=jd1,
        expected_jd_score=0.95, expected_top_role="AI 工程师",
    ))

    # Case 2: 部分匹配
    user2 = [
        {"skill": "Python", "level": "熟练", "weight": 0.8},
        {"skill": "Java", "level": "熟练", "weight": 0.7},
    ]
    cases.append(MatchTestCase(
        case_id="jd_partial_1", user_skills=user2, jd_record=jd1,
        expected_jd_score=0.4, expected_top_role="",
    ))

    # Case 3: Role Top-N
    role_cards = [
        {
            "role_id": "r1", "name": "AI 工程师", "category": "AI工程师", "level": "中级",
            "required_skills": [
                {"skill": "Python", "level": "熟练", "weight": 0.9},
                {"skill": "PyTorch", "level": "熟练", "weight": 0.8},
            ],
            "preferred_skills": [],
        },
        {
            "role_id": "r2", "name": "后端工程师", "category": "后端开发", "level": "中级",
            "required_skills": [
                {"skill": "Java", "level": "熟练", "weight": 0.9},
                {"skill": "MySQL", "level": "熟练", "weight": 0.7},
            ],
            "preferred_skills": [],
        },
    ]
    cases.append(MatchTestCase(
        case_id="role_topn_1", user_skills=user1, role_cards=role_cards,
        expected_jd_score=0.0, expected_top_role="AI 工程师",
    ))

    log.info(f"匹配测试集: {len(cases)} 个用例")
    return cases


def evaluate_matchers(
    jd_results: List[Dict[str, Any]],
    role_results: List[Dict[str, Any]],
    test_cases: List[MatchTestCase],
) -> Dict[str, float]:
    """评估匹配器

    :param jd_results: 来自 JDMatcher.match 的结果
    :param role_results: 来自 RoleMatcher.match_top_n 的 Top-1 列表
    """
    if not test_cases:
        return {"mae": 0.0, "top1_accuracy": 0.0}
    # JD: 平均绝对误差
    diffs: List[float] = []
    for i, r in enumerate(jd_results):
        if i >= len(test_cases):
            break
        if not r:
            continue
        diffs.append(abs(r.get("overall_score", 0) - test_cases[i].expected_jd_score))
    mae = sum(diffs) / max(1, len(diffs))

    # Role: Top-1 命中率
    correct = 0
    for i, top in enumerate(role_results):
        if i >= len(test_cases):
            break
        if not top:
            continue
        if top.get("name") == test_cases[i].expected_top_role:
            correct += 1
    top1 = correct / max(1, len(test_cases))
    log.info(f"匹配评估: MAE={mae:.3f}, Top1={top1:.2f}")
    return {
        "mae": round(mae, 3),
        "top1_accuracy": round(top1, 3),
        "jd_sample_size": len(diffs),
        "role_sample_size": len(role_results),
    }
