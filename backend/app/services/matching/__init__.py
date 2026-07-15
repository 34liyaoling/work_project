"""人岗匹配引擎（双匹配路径）

路径一: 与具体 JD 精准匹配（jd_matcher）
路径二: 与图谱岗位方向 Top-N 匹配（role_matcher）

多维度得分（权重从 config 读取）:
- α × 必备技能匹配率
- β × 加分技能匹配率
- γ × 技能深度匹配
- δ × 领域契合度
"""
from app.services.matching.scorer import Scorer, get_scorer
from app.services.matching.required_matcher import RequiredMatcher, get_required_matcher
from app.services.matching.preferred_matcher import PreferredMatcher, get_preferred_matcher
from app.services.matching.depth_matcher import DepthMatcher, get_depth_matcher
from app.services.matching.domain_matcher import DomainMatcher, get_domain_matcher
from app.services.matching.jd_matcher import JDMatcher, get_jd_matcher
from app.services.matching.role_matcher import RoleMatcher, get_role_matcher
from app.services.matching.gap_analyzer import GapAnalyzer, get_gap_analyzer
from app.services.matching.test_dataset import (
    build_match_test_set,
    evaluate_matchers,
    MatchTestCase,
)


__all__ = [
    "Scorer",
    "RequiredMatcher",
    "PreferredMatcher",
    "DepthMatcher",
    "DomainMatcher",
    "JDMatcher",
    "RoleMatcher",
    "GapAnalyzer",
    "MatchTestCase",
    "build_match_test_set",
    "evaluate_matchers",
    "get_scorer",
    "get_required_matcher",
    "get_preferred_matcher",
    "get_depth_matcher",
    "get_domain_matcher",
    "get_jd_matcher",
    "get_role_matcher",
    "get_gap_analyzer",
]
