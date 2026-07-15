"""岗位方向 Top-N 匹配（方式二）

对图谱中所有岗位卡片计算综合得分，返回 Top-N。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from app.core.logger import log
from app.services.matching.depth_matcher import DepthMatcher
from app.services.matching.domain_matcher import DomainMatcher
from app.services.matching.gap_analyzer import GapAnalyzer
from app.services.matching.preferred_matcher import PreferredMatcher
from app.services.matching.required_matcher import RequiredMatcher
from app.services.matching.scorer import Scorer


class RoleMatcher:
    """岗位方向 Top-N 匹配器"""

    def __init__(
        self,
        scorer: Optional[Scorer] = None,
        required: Optional[RequiredMatcher] = None,
        preferred: Optional[PreferredMatcher] = None,
        depth: Optional[DepthMatcher] = None,
        domain: Optional[DomainMatcher] = None,
        gap: Optional[GapAnalyzer] = None,
    ):
        self.scorer = scorer or Scorer()
        self.required = required or RequiredMatcher()
        self.preferred = preferred or PreferredMatcher()
        self.depth = depth or DepthMatcher()
        self.domain = domain or DomainMatcher()
        self.gap = gap or GapAnalyzer()

    def match_top_n(
        self,
        role_cards: Sequence[Dict[str, Any]],
        user_skills: Sequence[Dict[str, Any]],
        user_industries: Optional[Sequence[str]] = None,
        top_n: int = 10,
    ) -> List[Dict[str, Any]]:
        """对每个 role_card 计算综合分并按分排序返回 Top-N"""
        results: List[Dict[str, Any]] = []
        for role in role_cards or []:
            r = self.required.match(role.get("required_skills", []) or [], user_skills)
            p = self.preferred.match(role.get("preferred_skills", []) or [], user_skills)
            d = self.depth.match(role.get("required_skills", []) or [], user_skills)
            dm = self.domain.match(
                user_skills,
                target_category=role.get("category", ""),
                target_industries=role.get("industries"),
                user_industries=user_industries,
            )
            overall = self.scorer.compute({
                "required": r["score"],
                "preferred": p["score"],
                "depth": d["score"],
                "domain": dm["score"],
            })
            results.append({
                "role_id": role.get("role_id") or role.get("name"),
                "name": role.get("name") or role.get("job_title"),
                "category": role.get("category"),
                "level": role.get("level"),
                "overall_score": overall["overall_score"],
                "breakdown": overall["breakdown"],
                "missing_required": r["missing"],
            })
        results.sort(key=lambda x: x["overall_score"], reverse=True)
        top = results[: int(top_n)]
        log.info(f"Role Top-{top_n}: 最高分 {top[0]['overall_score'] if top else 0:.2f}")
        return top


_singleton: Optional[RoleMatcher] = None


def get_role_matcher() -> RoleMatcher:
    global _singleton
    if _singleton is None:
        _singleton = RoleMatcher()
    return _singleton
