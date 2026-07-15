"""技能差距分析

根据 target_required + target_preferred 与 user_skills 对比，
输出 gap_skills（用户缺少的技能 + 优先级）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from app.core.logger import log


class GapAnalyzer:
    """技能差距分析器"""

    def analyze(
        self,
        target_required: Sequence[Dict[str, Any]],
        target_preferred: Sequence[Dict[str, Any]],
        user_skills: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        user_set = {self._norm(s) for s in user_skills or []}
        gaps: List[Dict[str, Any]] = []
        for t in target_required or []:
            key = self._norm(t)
            if key in user_set:
                continue
            gaps.append({
                "skill": t.get("skill"),
                "level": t.get("level"),
                "weight": float(t.get("weight", 0.7) or 0.7),
                "priority": "P0",
                "category": t.get("category", "通用"),
                "type": "required",
            })
        for t in target_preferred or []:
            key = self._norm(t)
            if key in user_set:
                continue
            gaps.append({
                "skill": t.get("skill"),
                "level": t.get("level"),
                "weight": float(t.get("weight", 0.4) or 0.4),
                "priority": "P1",
                "category": t.get("category", "通用"),
                "type": "preferred",
            })
        gaps.sort(key=lambda x: (x["priority"], -x["weight"]))
        log.info(f"技能差距: {len(gaps)} 项 (P0={sum(1 for g in gaps if g['priority']=='P0')})")
        return gaps

    @staticmethod
    def _norm(skill: Any) -> str:
        if isinstance(skill, dict):
            return (skill.get("skill") or skill.get("standard_name") or "").strip().lower()
        return str(skill or "").strip().lower()


_singleton = None


def get_gap_analyzer() -> GapAnalyzer:
    global _singleton
    if _singleton is None:
        _singleton = GapAnalyzer()
    return _singleton
