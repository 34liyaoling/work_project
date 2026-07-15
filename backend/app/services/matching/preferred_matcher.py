"""加分技能匹配率计算"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from app.core.logger import log


class PreferredMatcher:
    """加分技能匹配器"""

    def match(
        self,
        target_preferred: Sequence[Dict[str, Any]],
        user_skills: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not target_preferred:
            return {"score": 0.0, "matched": [], "total_weight": 0.0}
        user_set = {self._norm(s) for s in user_skills or []}
        matched: List[Dict[str, Any]] = []
        total_w = 0.0
        hit_w = 0.0
        for t in target_preferred:
            w = float(t.get("weight", 0.3) or 0.3)
            total_w += w
            if self._norm(t) in user_set:
                hit_w += w
                matched.append({"skill": t.get("skill"), "weight": w})
        score = hit_w / total_w if total_w > 0 else 0.0
        log.info(f"加分匹配率={score:.2f}, matched={len(matched)}")
        return {
            "score": round(score, 4),
            "matched": matched,
            "total_weight": round(total_w, 3),
            "hit_weight": round(hit_w, 3),
        }

    @staticmethod
    def _norm(skill: Any) -> str:
        if isinstance(skill, dict):
            return (skill.get("skill") or skill.get("standard_name") or "").strip().lower()
        return str(skill or "").strip().lower()


_singleton = None


def get_preferred_matcher() -> PreferredMatcher:
    global _singleton
    if _singleton is None:
        _singleton = PreferredMatcher()
    return _singleton
