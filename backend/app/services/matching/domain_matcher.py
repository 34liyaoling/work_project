"""领域契合度计算

- 候选人的工作领域 / 行业与岗位领域越接近，分越高
- 基于 Jaccard + 类别层级 fallback
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from app.core.logger import log


# 类别相似度矩阵（手工定义）
CATEGORY_SIMILARITY: Dict[str, Dict[str, float]] = {
    "AI工程师": {"AI工程师": 1.0, "算法工程师": 0.8, "数据科学": 0.6, "后端开发": 0.4},
    "算法工程师": {"AI工程师": 0.8, "算法工程师": 1.0, "数据科学": 0.7},
    "数据科学": {"数据科学": 1.0, "AI工程师": 0.6, "数据工程": 0.7, "数据分析": 0.8},
    "后端开发": {"后端开发": 1.0, "DevOps": 0.6, "数据工程": 0.5},
    "前端开发": {"前端开发": 1.0, "设计师": 0.4},
    "数据工程": {"数据工程": 1.0, "数据科学": 0.7, "后端开发": 0.5},
}


class DomainMatcher:
    """领域契合度计算器"""

    def match(
        self,
        user_skills: Sequence[Dict[str, Any]],
        target_category: str,
        target_industries: Sequence[str] = None,
        user_industries: Sequence[str] = None,
    ) -> Dict[str, Any]:
        """根据用户技能类别 + 行业与目标岗位类别对比"""
        if not target_category:
            return {"score": 0.0, "explanation": "no_target_category"}
        user_categories = {s.get("category", "通用") for s in user_skills or []}
        # 1. 类别相似度
        best_sim = 0.0
        sim_map = CATEGORY_SIMILARITY.get(target_category, {})
        for cat in user_categories:
            best_sim = max(best_sim, sim_map.get(cat, 0.0))
        # 2. 行业重合
        user_ind = set(user_industries or [])
        target_ind = set(target_industries or [])
        if user_ind and target_ind:
            jaccard = len(user_ind & target_ind) / max(1, len(user_ind | target_ind))
        else:
            jaccard = 0.0
        # 加权融合
        score = round(0.7 * best_sim + 0.3 * jaccard, 4)
        log.info(f"领域契合度={score:.2f} (类别={best_sim:.2f}, 行业={jaccard:.2f})")
        return {
            "score": score,
            "category_similarity": round(best_sim, 3),
            "industry_jaccard": round(jaccard, 3),
            "user_categories": sorted(user_categories),
            "target_category": target_category,
        }


_singleton = None


def get_domain_matcher() -> DomainMatcher:
    global _singleton
    if _singleton is None:
        _singleton = DomainMatcher()
    return _singleton
