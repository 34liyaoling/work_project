"""置信度评估

对岗位定义中的每条技能计算综合置信度，规则:
- skill_confidence: 单一技能在数据集中被提及的频次归一化得分
- cross_source_bonus: 出现在多个数据源时加分
- recency_bonus: 近期出现的 JD 占比高时加分
- 总置信度 < 0.7 的技能不纳入必备清单（required_skills）
"""
from __future__ import annotations

import math
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from app.core.config import settings
from app.core.logger import log


class ConfidenceEvaluator:
    """置信度评估器"""

    def __init__(self, threshold: Optional[float] = None):
        self.threshold = threshold if threshold is not None else settings.CONFIDENCE_THRESHOLD

    def evaluate_skills(
        self,
        skill_candidates: Sequence[Dict[str, Any]],
        jd_records: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """对候选技能列表逐条计算置信度

        :param skill_candidates: [{"skill":"Python","level":"熟练","weight":0.7}]
        :param jd_records: 支撑 JD 列表（含 source / company / published_at / skills）
        :return: 增强后的技能列表（含 confidence / evidence_count / sources）
        """
        jd_records = jd_records or []
        skill_stats = self._aggregate_skill_stats(jd_records)
        results: List[Dict[str, Any]] = []
        for cand in skill_candidates:
            skill = (cand.get("skill") or "").strip()
            if not skill:
                continue
            stats = skill_stats.get(skill.lower(), {"count": 0, "sources": set()})
            confidence = self._compute_confidence(
                cand.get("weight", 0.5),
                stats.get("count", 0),
                len(stats.get("sources", set())),
                max(1, len(jd_records)),
            )
            results.append({
                **cand,
                "confidence": round(confidence, 3),
                "evidence_count": stats.get("count", 0),
                "sources": sorted(stats.get("sources", set())),
                "is_required": confidence >= self.threshold,
            })
        return results

    def filter_required(self, evaluated_skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤出置信度 >= threshold 的技能（纳入必备清单）"""
        return [s for s in evaluated_skills if s.get("is_required")]

    def filter_preferred(self, evaluated_skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """其余技能纳入加分清单"""
        return [s for s in evaluated_skills if not s.get("is_required")]

    # ----------------- 内部 -----------------
    def _aggregate_skill_stats(self, jd_records: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        stats: Dict[str, Dict[str, Any]] = {}
        for jd in jd_records:
            source = (jd.get("source") or "unknown").lower()
            for s in jd.get("skills", []) or []:
                key = s.lower()
                entry = stats.setdefault(key, {"count": 0, "sources": set()})
                entry["count"] += 1
                entry["sources"].add(source)
        return stats

    def _compute_confidence(
        self,
        declared_weight: float,
        evidence_count: int,
        source_count: int,
        total_jds: int,
    ) -> float:
        """综合置信度计算

        confidence = 0.5 * weight
                   + 0.2 * min(evidence_count / max(1, total_jds), 1)
                   + 0.2 * min(source_count / 3, 1)
                   + 0.1 * 证据量奖励(log缩放)
        """
        try:
            w = max(0.0, min(float(declared_weight), 1.0))
        except Exception:
            w = 0.5
        coverage = min(evidence_count / max(1, total_jds), 1.0)
        source_diversity = min(source_count / 3.0, 1.0)
        # log 缩放防止极热技能爆分
        evidence_bonus = math.log1p(evidence_count) / math.log1p(20)
        score = 0.5 * w + 0.2 * coverage + 0.2 * source_diversity + 0.1 * min(evidence_bonus, 1.0)
        return max(0.0, min(score, 1.0))


_singleton: Optional[ConfidenceEvaluator] = None


def get_confidence_evaluator() -> ConfidenceEvaluator:
    global _singleton
    if _singleton is None:
        _singleton = ConfidenceEvaluator()
    return _singleton
