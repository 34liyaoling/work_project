"""数据可信度评分

评分维度：
    1. **来源权重** - 不同数据源的可信度（企业官网 > 头部招聘平台 > 第三方 > 行业报告）
    2. **时效性**   - 距今越久评分越低；超过 2 年的 JD 大幅降权（可配置）
    3. **完整性**   - 字段缺失越多评分越低
    4. **文本质量** - 文本长度过短 / 重复度过高 / 模板化 → 降权
    5. **交叉验证加成** - 多源/多公司共现 → 加分

最终 score ∈ [0, 1]，>0.7 可信；<0.4 进入审核。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logger import log


# 来源权重表（可在 .env 中覆盖）
DEFAULT_SOURCE_WEIGHTS: Dict[str, float] = {
    # 头部招聘平台
    "boss": 0.85,
    "zhilian": 0.80,
    "liepin": 0.82,
    "lagou": 0.78,
    "linkedin": 0.85,
    # 企业官网（一般最权威）
    "enterprise": 0.90,
    # 行业研究 / 政策
    "industry_report": 0.55,
    "policy": 0.70,
    # 行业标准
    "onet": 0.88,
    # 未知来源
    "unknown": 0.40,
    "mock": 0.30,
}

# 字段完整度权重
FIELD_WEIGHTS: Dict[str, float] = {
    "title": 0.15,
    "company": 0.15,
    "category": 0.10,
    "level": 0.10,
    "location": 0.05,
    "salary_range": 0.10,
    "raw_text": 0.20,
    "skills": 0.10,
    "published_at": 0.05,
}


@dataclass
class CredibilityDetail:
    """详细分维度评分"""

    source_score: float
    freshness_score: float
    completeness_score: float
    text_quality_score: float
    cross_source_bonus: float
    final_score: float
    reasons: List[str]


class CredibilityScorer:
    """数据可信度评分器

    用法:
        scorer = CredibilityScorer()
        detail = scorer.score(jd_dict)
        jd_dict["credibility_score"] = detail.final_score
    """

    def __init__(
        self,
        source_weights: Optional[Dict[str, float]] = None,
        stale_years: Optional[int] = None,
        min_text_length: int = 200,
    ) -> None:
        self.source_weights = source_weights or DEFAULT_SOURCE_WEIGHTS
        self.stale_years = int(stale_years or settings.STALE_JD_YEARS)
        self.min_text_length = int(min_text_length)

    # -------------------------------------------------------- 单条
    def score(self, item: Dict[str, Any]) -> CredibilityDetail:
        source_score = self._score_source(item)
        freshness_score = self._score_freshness(item)
        completeness_score = self._score_completeness(item)
        text_quality_score = self._score_text_quality(item)
        cross_bonus = float(item.get("cross_source_bonus", 0.0))  # 由 cross_validator 注入

        # 加权汇总
        final = (
            0.30 * source_score
            + 0.25 * freshness_score
            + 0.20 * completeness_score
            + 0.15 * text_quality_score
            + 0.10 * cross_bonus
        )
        final = round(max(0.0, min(1.0, final)), 4)

        reasons: List[str] = []
        if source_score < 0.5:
            reasons.append(f"low_source={item.get('source', '?')}")
        if freshness_score < 0.5:
            reasons.append("stale_jd")
        if completeness_score < 0.5:
            reasons.append("incomplete")
        if text_quality_score < 0.5:
            reasons.append("low_text_quality")
        if cross_bonus > 0.5:
            reasons.append("strong_cross_evidence")

        return CredibilityDetail(
            source_score=round(source_score, 4),
            freshness_score=round(freshness_score, 4),
            completeness_score=round(completeness_score, 4),
            text_quality_score=round(text_quality_score, 4),
            cross_source_bonus=round(cross_bonus, 4),
            final_score=final,
            reasons=reasons,
        )

    def score_batch(self, items: List[Dict[str, Any]]) -> List[CredibilityDetail]:
        return [self.score(it) for it in items]

    # -------------------------------------------------------- 维度
    def _score_source(self, item: Dict[str, Any]) -> float:
        src = (item.get("source") or "unknown").lower()
        return self.source_weights.get(src, self.source_weights["unknown"])

    def _score_freshness(self, item: Dict[str, Any]) -> float:
        ts = item.get("published_at")
        if not ts:
            return 0.5
        try:
            if isinstance(ts, str):
                # 兼容 ISO / 多种格式
                ts_clean = ts.replace("Z", "").replace("T", " ")
                pub = datetime.fromisoformat(ts_clean[:19])
            elif isinstance(ts, datetime):
                pub = ts
            else:
                return 0.5
        except Exception:  # noqa: BLE001
            return 0.5
        days = (datetime.now() - pub).days
        years = days / 365.0
        if years <= 0.5:
            return 1.0
        if years <= 1.0:
            return 0.9
        if years <= self.stale_years:
            return 0.7
        if years <= self.stale_years + 1:
            return 0.4
        return 0.2

    def _score_completeness(self, item: Dict[str, Any]) -> float:
        score = 0.0
        for field_name, weight in FIELD_WEIGHTS.items():
            v = item.get(field_name)
            ok = False
            if isinstance(v, str):
                ok = bool(v.strip())
            elif isinstance(v, (list, dict)):
                ok = len(v) > 0
            elif isinstance(v, (int, float)):
                ok = v > 0
            elif v is not None:
                ok = True
            if ok:
                score += weight
        return min(score, 1.0)

    def _score_text_quality(self, item: Dict[str, Any]) -> float:
        text = item.get("raw_text") or ""
        if not text:
            return 0.2
        L = len(text)
        # 太短
        if L < 50:
            return 0.3
        # 长度评分：足够长最好
        len_score = min(L / 1500.0, 1.0)
        # 重复度：行重复比例
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return 0.4
        unique_ratio = len(set(lines)) / len(lines)
        if unique_ratio < 0.4:
            return 0.3  # 大量重复行 → 模板
        # 模板化关键词密度
        noisy = [
            "优秀的沟通", "良好的沟通", "责任心", "抗压", "团队合作", "学习能力",
        ]
        noise_count = sum(1 for kw in noisy if kw in text)
        noise_penalty = min(noise_count * 0.1, 0.4)
        base = 0.5 + 0.3 * len_score + 0.2 * unique_ratio
        return round(max(0.0, min(1.0, base - noise_penalty)), 4)


# ============================================================
# 便捷
# ============================================================
_default_scorer: Optional[CredibilityScorer] = None


def get_credibility_scorer() -> CredibilityScorer:
    global _default_scorer
    if _default_scorer is None:
        _default_scorer = CredibilityScorer()
    return _default_scorer


__all__ = [
    "CredibilityScorer",
    "CredibilityDetail",
    "DEFAULT_SOURCE_WEIGHTS",
    "get_credibility_scorer",
]
