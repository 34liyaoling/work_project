"""四层幻觉防控编排器

按 Layer1 → Layer2 → Layer3 → Layer4 顺序执行，每层决定是否放行或转人工。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from app.core.config import settings
from app.core.logger import log
from app.services.hallucination_guard.layer1_source import SourceFilter
from app.services.hallucination_guard.layer2_cross import CrossValidator
from app.services.hallucination_guard.layer3_selfcheck import LLMSelfChecker
from app.services.hallucination_guard.layer4_human import HumanReviewQueue


class HallucinationGuard:
    """四层防控编排器"""

    SELFCHECK_PASS_SCORE = 7.0  # Layer3 评分 >= 该值认为通过
    SELFCHECK_REVIEW_SCORE = 5.0  # < 该值直接转人工

    def __init__(
        self,
        source_filter: Optional[SourceFilter] = None,
        cross_validator: Optional[CrossValidator] = None,
        self_checker: Optional[LLMSelfChecker] = None,
        human_queue: Optional[HumanReviewQueue] = None,
    ):
        self.layer1 = source_filter or SourceFilter()
        self.layer2 = cross_validator or CrossValidator()
        self.layer3 = self_checker or LLMSelfChecker()
        self.layer4 = human_queue or HumanReviewQueue()

    async def guard_records(
        self,
        jd_records: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """对原始 JD 数据流执行 Layer1 过滤"""
        kept = self.layer1.filter_records(jd_records)
        return {
            "layer1_input": len(jd_records),
            "layer1_passed": len(kept),
            "kept": kept,
        }

    async def guard_role_card(
        self,
        role_card: Dict[str, Any],
        jd_records: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """对单个岗位定义卡片执行 Layer2-Layer4 防控"""
        # Layer2
        l2 = self.layer2.validate_role(role_card, jd_records)
        if not l2["passes"]:
            self.layer4.enqueue(
                "jobrole",
                role_card.get("job_title", "unknown"),
                role_card,
                f"Layer2 验证未通过 (onet_score={l2['onet_score']}, conf={l2['confidence_score']})",
            )
            return {
                "action": "human_review",
                "layer": 2,
                "detail": l2,
            }
        # Layer3
        l3 = await self.layer3.check(role_card)
        overall = float(l3.get("overall", 0))
        if overall < self.SELFCHECK_REVIEW_SCORE:
            self.layer4.enqueue(
                "jobrole",
                role_card.get("job_title", "unknown"),
                {"role_card": role_card, "selfcheck": l3},
                f"Layer3 自检评分过低 ({overall})",
            )
            return {"action": "human_review", "layer": 3, "detail": l3}
        if overall < self.SELFCHECK_PASS_SCORE:
            return {"action": "conditional_pass", "layer": 3, "detail": l3}
        return {"action": "pass", "layer": 3, "detail": l3}


_singleton: Optional[HallucinationGuard] = None


def get_guard() -> HallucinationGuard:
    global _singleton
    if _singleton is None:
        _singleton = HallucinationGuard()
    return _singleton
