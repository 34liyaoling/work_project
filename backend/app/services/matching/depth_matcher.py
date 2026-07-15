"""技能深度匹配

对每条匹配上的技能，比较"用户水平"与"岗位要求水平"的偏差：
- 用户水平 = "基础" 0.4 / "熟练" 0.7 / "精通" 1.0
- 偏差 = |用户分 - 要求分| / 1.0
- 深度分 = 1 - mean(偏差)
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from app.core.logger import log


LEVEL_SCORE: Dict[str, float] = {
    "基础": 0.4,
    "熟练": 0.7,
    "精通": 1.0,
}


class DepthMatcher:
    """技能深度匹配器"""

    def match(
        self,
        target_required: Sequence[Dict[str, Any]],
        user_skills: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """返回深度匹配分"""
        user_map = {
            (s.get("skill") or s.get("standard_name") or "").strip().lower(): s
            for s in user_skills or []
        }
        deviations: List[float] = []
        per_skill: List[Dict[str, Any]] = []
        for t in target_required or []:
            t_name = (t.get("skill") or "").strip().lower()
            if not t_name:
                continue
            target_score = LEVEL_SCORE.get(t.get("level", "熟练"), 0.7)
            user_skill = user_map.get(t_name)
            if not user_skill:
                # 用户完全不具备此技能，按"深度不足"处理
                per_skill.append({
                    "skill": t.get("skill"),
                    "target_level": t.get("level", "熟练"),
                    "user_level": None,
                    "deviation": 1.0,
                })
                deviations.append(1.0)
                continue
            user_score = LEVEL_SCORE.get(user_skill.get("level", "熟练"), 0.7)
            deviation = abs(target_score - user_score)
            deviations.append(deviation)
            per_skill.append({
                "skill": t.get("skill"),
                "target_level": t.get("level", "熟练"),
                "user_level": user_skill.get("level"),
                "deviation": round(deviation, 3),
            })
        if not deviations:
            return {"score": 0.0, "per_skill": []}
        avg_dev = sum(deviations) / len(deviations)
        score = max(0.0, 1.0 - avg_dev)
        log.info(f"深度匹配分={score:.2f} (平均偏差 {avg_dev:.2f})")
        return {
            "score": round(score, 4),
            "average_deviation": round(avg_dev, 3),
            "per_skill": per_skill,
        }


_singleton = None


def get_depth_matcher() -> DepthMatcher:
    global _singleton
    if _singleton is None:
        _singleton = DepthMatcher()
    return _singleton
