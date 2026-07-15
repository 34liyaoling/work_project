"""JD 精准匹配（方式一）"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from app.core.logger import log
from app.services.matching.depth_matcher import DepthMatcher
from app.services.matching.domain_matcher import DomainMatcher
from app.services.matching.gap_analyzer import GapAnalyzer
from app.services.matching.preferred_matcher import PreferredMatcher
from app.services.matching.required_matcher import RequiredMatcher
from app.services.matching.scorer import Scorer


class JDMatcher:
    """JD 精准匹配器"""

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

    def match(
        self,
        jd_record: Dict[str, Any],
        user_skills: Sequence[Dict[str, Any]],
        user_industries: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """对单个 JD 做匹配"""
        parsed = jd_record.get("parsed_data") or {}
        required = parsed.get("required_skills", []) or []
        preferred = parsed.get("preferred_skills", []) or []

        r = self.required.match(required, user_skills)
        p = self.preferred.match(preferred, user_skills)
        d = self.depth.match(required, user_skills)
        dm = self.domain.match(
            user_skills,
            target_category=parsed.get("category", ""),
            target_industries=parsed.get("industries"),
            user_industries=user_industries,
        )

        overall = self.scorer.compute({
            "required": r["score"],
            "preferred": p["score"],
            "depth": d["score"],
            "domain": dm["score"],
        })

        gap = self.gap.analyze(required, preferred, user_skills)

        return {
            "target_id": jd_record.get("jd_id") or jd_record.get("id"),
            "target_type": "jd",
            "target_title": parsed.get("job_title") or jd_record.get("title"),
            "company": jd_record.get("company"),
            "overall_score": overall["overall_score"],
            "breakdown": overall["breakdown"],
            "weights": overall["weights"],
            "matched_required": r["matched"],
            "missing_required": r["missing"],
            "gap_skills": gap,
            "domain": dm,
        }


_singleton: Optional[JDMatcher] = None


def get_jd_matcher() -> JDMatcher:
    global _singleton
    if _singleton is None:
        _singleton = JDMatcher()
    return _singleton
