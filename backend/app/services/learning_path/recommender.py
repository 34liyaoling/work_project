"""学习改进建议生成

基于 gap_skills + 用户画像 + 路径结果生成可读建议列表
（recommendations）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from app.core.logger import log


class Recommender:
    """改进建议生成器"""

    def recommend(
        self,
        gap_skills: Sequence[Dict[str, Any]],
        learning_path: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """根据 gap 与学习路径生成自然语言建议

        :return: [{"priority":"P0|P1", "skill":"...", "suggestion":"..."}]
        """
        recs: List[Dict[str, Any]] = []
        for g in gap_skills or []:
            skill = g.get("skill")
            if not skill:
                continue
            recs.append({
                "priority": g.get("priority", "P1"),
                "skill": skill,
                "category": g.get("category", "通用"),
                "suggestion": self._build_suggestion(g),
            })
        if learning_path and learning_path.get("phases"):
            first_phase = learning_path["phases"][0]
            recs.append({
                "priority": "P0",
                "skill": "学习路径起点",
                "category": "规划",
                "suggestion": (
                    f"建议从阶段 1 开始（{', '.join(first_phase.get('skills', []))}），"
                    f"预计投入 {first_phase.get('estimated_hours', 0)} 小时"
                ),
            })
        recs.sort(key=lambda x: (x["priority"], x["skill"]))
        log.info(f"改进建议: {len(recs)} 条")
        return recs

    @staticmethod
    def _build_suggestion(g: Dict[str, Any]) -> str:
        skill = g.get("skill")
        level = g.get("level", "熟练")
        priority = g.get("priority", "P1")
        kind = g.get("type", "required")
        if priority == "P0":
            return (
                f"【必备】建议优先学习「{skill}」至{level}水平。"
                f"该技能被目标岗位明确要求，掌握后能显著提升匹配率。"
            )
        if kind == "preferred":
            return (
                f"【加分】如有余力建议学习「{skill}」，"
                f"掌握后属于亮点技能，可作为简历加分项。"
            )
        return f"建议补齐技能「{skill}」"


_singleton: Optional[Recommender] = None


def get_recommender() -> Recommender:
    global _singleton
    if _singleton is None:
        _singleton = Recommender()
    return _singleton
