"""必备技能匹配率计算

required_score = sum(hit_skill_weight) / sum(target_skill_weight)
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from app.core.logger import log


class RequiredMatcher:
    """必备技能匹配器"""

    def match(
        self,
        target_required: Sequence[Dict[str, Any]],
        user_skills: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """必备技能匹配率

        target_required: [{"skill":"Python","weight":0.8,"level":"熟练"}]
        user_skills: [{"skill":"Python","level":"熟练","weight":0.7}, ...]
        """
        if not target_required:
            return {"score": 0.0, "matched": [], "missing": [], "total_weight": 0.0}
        user_set = {self._norm(s) for s in user_skills or []}
        matched: List[Dict[str, Any]] = []
        missing: List[Dict[str, Any]] = []
        total_w = 0.0
        hit_w = 0.0
        for t in target_required:
            w = float(t.get("weight", 0.5) or 0.5)
            total_w += w
            if self._norm(t) in user_set:
                hit_w += w
                matched.append({"skill": t.get("skill"), "weight": w})
            else:
                missing.append({"skill": t.get("skill"), "weight": w})
        score = hit_w / total_w if total_w > 0 else 0.0
        log.info(f"必备匹配率={score:.2f}, matched={len(matched)}, missing={len(missing)}")
        return {
            "score": round(score, 4),
            "matched": matched,
            "missing": missing,
            "total_weight": round(total_w, 3),
            "hit_weight": round(hit_w, 3),
        }

    @staticmethod
    def _norm(skill: Any) -> str:
        if isinstance(skill, dict):
            return (skill.get("skill") or skill.get("standard_name") or "").strip().lower()
        return str(skill or "").strip().lower()


_singleton = None


def get_required_matcher() -> RequiredMatcher:
    global _singleton
    if _singleton is None:
        _singleton = RequiredMatcher()
    return _singleton
