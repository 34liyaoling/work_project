"""第一层 - 数据来源过滤

按数据源可信度与时效性打分，丢弃低质数据。

可信度评分规则:
- 平台已知 + 官方 / API → 0.9
- 平台已知 + 网页爬取 → 0.7
- 来源未知 → 0.4

时效性: 发布时间距今 > STALE_JD_YEARS 年视为过期，credibility *= 0.5
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from app.core.config import settings
from app.core.logger import log


# 平台可信度基础分
SOURCE_BASE_CREDIBILITY: Dict[str, float] = {
    "boss": 0.8,
    "lagou": 0.75,
    "liepin": 0.8,
    "zhilian": 0.7,
    "linkedin": 0.85,
    "job51": 0.7,
    "internal": 0.9,
    "official": 0.95,
    "onet": 0.95,
}


class SourceFilter:
    """第一层过滤器"""

    def __init__(
        self,
        min_credibility: float = 0.4,
        stale_years: Optional[int] = None,
    ):
        self.min_credibility = min_credibility
        self.stale_years = stale_years if stale_years is not None else settings.STALE_JD_YEARS

    def score(self, record: Dict[str, Any]) -> float:
        """对单条数据计算可信度"""
        source = (record.get("source") or "unknown").lower()
        base = SOURCE_BASE_CREDIBILITY.get(source, 0.4)

        # 时效性惩罚
        published = self._parse_date(record.get("published_at"))
        if published:
            age = datetime.utcnow() - published
            if age > timedelta(days=365 * self.stale_years):
                base *= 0.5
                log.debug(f"过期 JD: source={source} age={age.days}d")
        # 内容长度奖励（更长的 JD 倾向更具体）
        text = record.get("raw_text") or record.get("text") or ""
        if len(text) > 1000:
            base = min(1.0, base + 0.05)
        elif len(text) < 100:
            base *= 0.7
        return round(base, 3)

    def filter_records(
        self,
        records: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """过滤低可信度数据，附加 credibility_score 字段"""
        result: List[Dict[str, Any]] = []
        for r in records or []:
            score = self.score(r)
            if score < self.min_credibility:
                log.debug(f"丢弃低可信度数据 source={r.get('source')}, score={score}")
                continue
            r2 = dict(r)
            r2["credibility_score"] = score
            result.append(r2)
        log.info(f"Layer1 过滤: 输入 {len(records)} → 通过 {len(result)}")
        return result

    @staticmethod
    def _parse_date(value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None


_singleton: Optional[SourceFilter] = None


def get_source_filter() -> SourceFilter:
    global _singleton
    if _singleton is None:
        _singleton = SourceFilter()
    return _singleton
