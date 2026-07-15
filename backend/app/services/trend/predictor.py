"""新兴技能需求预测

综合 trend 关键词 + JD 关联 + 前瞻性信号 + 历史 JD 频次趋势，
输出每个技能未来 6-12 个月的需求增长预测。
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from app.core.logger import log


class SkillPredictor:
    """技能需求预测器"""

    def __init__(self, horizon_months: int = 6):
        self.horizon_months = horizon_months

    def predict(
        self,
        correlations: Sequence[Dict[str, Any]],
        signals: Sequence[Dict[str, Any]],
        historical_skill_counts: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """输出每个技能的预测结果

        historical_skill_counts: [{"skill":..., "year":2025, "count":123}, ...]
        :return: [{"skill":"...", "phase":"...", "growth":"rising|stable|declining",
                    "predicted_growth":0.0-1.0, "rationale":...}]
        """
        historical = historical_skill_counts or []
        # 索引历史数据
        history_index: Dict[str, List[Dict[str, Any]]] = {}
        for item in historical:
            history_index.setdefault(item.get("skill", "").lower(), []).append(item)

        results: List[Dict[str, Any]] = []
        for corr in correlations or []:
            for emerging in corr.get("emerging_skills", []) or []:
                history = history_index.get(emerging.lower(), [])
                growth = self._historical_growth(history)
                phase = self._phase(corr, signals, emerging)
                score = self._predict_score(growth, phase, corr.get("jd_mention_count", 0))
                results.append({
                    "skill": emerging,
                    "phase": phase,
                    "growth": "rising" if growth > 0.05 else ("stable" if growth > -0.05 else "declining"),
                    "predicted_growth": round(score, 3),
                    "historical_growth": round(growth, 3),
                    "jd_mention_count": int(corr.get("jd_mention_count", 0) or 0),
                    "source_trend": corr.get("trend"),
                    "rationale": self._explain(corr, phase, growth, score),
                })
        # 排序取 top
        results.sort(key=lambda x: x["predicted_growth"], reverse=True)
        log.info(f"预测输出: {len(results)} 个技能")
        return results

    @staticmethod
    def _historical_growth(history: List[Dict[str, Any]]) -> float:
        """根据 (year, count) 序列计算年化增长率（CAGR 近似）"""
        if len(history) < 2:
            return 0.0
        history_sorted = sorted(history, key=lambda x: x.get("year", 0))
        first = history_sorted[0]
        last = history_sorted[-1]
        c0 = max(1, int(first.get("count", 1)))
        c1 = max(1, int(last.get("count", 1)))
        years = max(1, int(last.get("year", 0)) - int(first.get("year", 0)))
        try:
            cagr = (c1 / c0) ** (1.0 / years) - 1.0
        except Exception:
            cagr = 0.0
        return max(min(cagr, 5.0), -1.0)

    def _phase(
        self,
        corr: Dict[str, Any],
        signals: Sequence[Dict[str, Any]],
        skill: str,
    ) -> str:
        for s in signals or []:
            if (s.get("keyword") or "").strip().lower() == skill.lower():
                return s.get("phase", "adopting")
        return "adopting"

    def _predict_score(self, historical_growth: float, phase: str, jd_mentions: int) -> float:
        """综合得分 (0-1)

        score = 0.4 * sigmoid(historical_growth)
              + 0.3 * phase_weight
              + 0.3 * sigmoid(log(1+jd_mentions)/log(50))
        """
        hist_score = 1.0 / (1.0 + math.exp(-3 * historical_growth))
        phase_weight = {"mainstream": 0.7, "adopting": 0.85, "watchlist": 0.4}.get(phase, 0.5)
        jd_score = math.log1p(max(0, jd_mentions)) / math.log(50)
        jd_score = min(1.0, max(0.0, jd_score))
        return 0.4 * hist_score + 0.3 * phase_weight + 0.3 * jd_score

    @staticmethod
    def _explain(corr: Dict[str, Any], phase: str, growth: float, score: float) -> str:
        return (
            f"由趋势「{corr.get('trend')}」驱动，"
            f"历史增长 {growth:.2%}，阶段={phase}，"
            f"综合预测分 {score:.2f}"
        )


_singleton: Optional[SkillPredictor] = None


def get_skill_predictor() -> SkillPredictor:
    global _singleton
    if _singleton is None:
        _singleton = SkillPredictor()
    return _singleton
