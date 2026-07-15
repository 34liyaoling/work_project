"""多平台交叉验证

对同一"岗位定义"在 ≥3 个平台出现 → 高置信
            在 1 个平台出现   → 低置信（需人工审核）

工作流程：
    1. 按"标准化岗位签名"分组（签名 = 类别 + 主技能集合 + 级别）
    2. 统计每个签名出现的 source 数 / JD 数 / 公司数
    3. 给出 confidence 评分：>=3 源 → 高置信；==1 源 → 低置信

注意：低置信不删除，而是打标签，由 :class:`risk_handler` 推入审核队列。
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.config import settings
from app.core.logger import log


# ============================================================
# 数据结构
# ============================================================
@dataclass
class ValidationResult:
    """单条 JD 的验证结果"""

    jd_id: str
    signature: str
    source_count: int
    jd_count: int
    company_count: int
    confidence: float
    level: str  # "high" / "medium" / "low"
    reasons: List[str] = field(default_factory=list)


@dataclass
class CrossValidationGroup:
    """同一签名的所有 JD"""

    signature: str
    items: List[Dict[str, Any]] = field(default_factory=list)
    sources: Set[str] = field(default_factory=set)
    companies: Set[str] = field(default_factory=set)

    def source_count(self) -> int:
        return len(self.sources)

    def jd_count(self) -> int:
        return len(self.items)

    def company_count(self) -> int:
        return len(self.companies)


# ============================================================
# 主类
# ============================================================
class CrossValidator:
    """多平台交叉验证

    Attributes:
        high_source_threshold: 达到此源数即视为高置信（默认 3）
        low_source_threshold: 仅 1 源即视为低置信
    """

    def __init__(
        self,
        high_source_threshold: Optional[int] = None,
        low_source_threshold: int = 1,
    ) -> None:
        self.high_source_threshold = int(
            high_source_threshold
            if high_source_threshold is not None
            else settings.HIGH_CONFIDENCE_SOURCES
        )
        self.low_source_threshold = int(low_source_threshold)

    # -------------------------------------------------------- 签名生成
    @staticmethod
    def make_signature(item: Dict[str, Any]) -> str:
        """生成"岗位签名"：类别 + 主技能集合（top 5）+ 级别

        用于聚合相似岗位做交叉验证。
        """
        category = (item.get("category") or "").strip()
        level = (item.get("level") or "").strip()
        # 技能来源：优先标准化后的 skills；否则从 raw_text 简单提
        skills = item.get("skills") or []
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        if not skills:
            skills = []
        # 取前 5 个技能并归一化排序
        top5 = sorted(set(s.strip().lower() for s in skills[:10]))[:5]
        sig_raw = f"{category}|{level}|{'|'.join(top5)}"
        return hashlib.sha1(sig_raw.encode("utf-8")).hexdigest()[:16]

    # -------------------------------------------------------- 聚合
    def group_by_signature(self, items: List[Dict[str, Any]]) -> Dict[str, CrossValidationGroup]:
        """按签名分组"""
        groups: Dict[str, CrossValidationGroup] = {}
        for it in items:
            sig = self.make_signature(it)
            g = groups.setdefault(sig, CrossValidationGroup(signature=sig))
            g.items.append(it)
            src = (it.get("source") or "").strip()
            if src:
                g.sources.add(src)
            company = (it.get("company") or "").strip()
            if company:
                g.companies.add(company)
        return groups

    # -------------------------------------------------------- 验证
    def validate_item(
        self,
        item: Dict[str, Any],
        groups: Optional[Dict[str, CrossValidationGroup]] = None,
    ) -> ValidationResult:
        """验证单条 JD 的置信度"""
        if groups is None:
            groups = self.group_by_signature([item])
        sig = self.make_signature(item)
        g = groups.get(sig)
        if g is None:
            return ValidationResult(
                jd_id=item.get("jd_id", ""),
                signature=sig,
                source_count=0,
                jd_count=0,
                company_count=0,
                confidence=0.0,
                level="low",
                reasons=["no_group"],
            )
        sc = g.source_count()
        jc = g.jd_count()
        cc = g.company_count()
        # 评分：源数 0.5 + 公司数 0.3 + JD 数 0.2（饱和）
        score = min(
            1.0,
            0.5 * min(sc / max(self.high_source_threshold, 1), 1.0)
            + 0.3 * min(cc / 3.0, 1.0)
            + 0.2 * min(jc / 5.0, 1.0),
        )
        if sc >= self.high_source_threshold:
            level = "high"
        elif sc <= self.low_source_threshold:
            level = "low"
        else:
            level = "medium"
        reasons: List[str] = []
        if sc >= self.high_source_threshold:
            reasons.append(f"cross_{sc}_sources")
        if cc >= 2:
            reasons.append(f"diverse_{cc}_companies")
        if jc >= 5:
            reasons.append(f"freq_{jc}_jds")
        return ValidationResult(
            jd_id=item.get("jd_id", ""),
            signature=sig,
            source_count=sc,
            jd_count=jc,
            company_count=cc,
            confidence=round(score, 4),
            level=level,
            reasons=reasons,
        )

    def validate_batch(self, items: List[Dict[str, Any]]) -> List[ValidationResult]:
        """批量验证"""
        groups = self.group_by_signature(items)
        results = [self.validate_item(it, groups) for it in items]
        high = sum(1 for r in results if r.level == "high")
        med = sum(1 for r in results if r.level == "medium")
        low = sum(1 for r in results if r.level == "low")
        log.info(
            f"交叉验证完成：total={len(results)} high={high} medium={med} low={low}"
        )
        return results

    def filter_low_confidence(
        self,
        results: List[ValidationResult],
    ) -> List[ValidationResult]:
        """筛出低置信度（推入审核队列）"""
        return [r for r in results if r.level == "low"]


__all__ = [
    "CrossValidator",
    "ValidationResult",
    "CrossValidationGroup",
]
