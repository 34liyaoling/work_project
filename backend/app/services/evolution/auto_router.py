"""置信度评估与自动更新/人工审核路由

规则:
- source_count >= HIGH_CONFIDENCE_SOURCES 且 confidence >= CONFIDENCE_THRESHOLD → auto_apply
- 否则 → human_review
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logger import log


class AutoRouter:
    """自动/人工路由决策器"""

    def __init__(
        self,
        high_confidence_sources: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
    ):
        self.high_confidence_sources = (
            high_confidence_sources
            if high_confidence_sources is not None
            else settings.HIGH_CONFIDENCE_SOURCES
        )
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.CONFIDENCE_THRESHOLD
        )

    def route(self, change_event: Dict[str, Any]) -> Dict[str, Any]:
        """根据事件元数据决定路由

        :param change_event: 至少包含 confidence / source_count / type
        :return: {"action":"auto_apply|human_review", "reason":"..."}
        """
        confidence = float(change_event.get("confidence", 0.0) or 0.0)
        source_count = int(change_event.get("source_count", 0) or 0)
        change_type = change_event.get("type", "modified")

        # 删除类变更总是需要人工确认
        if change_type == "removed":
            return {
                "action": "human_review",
                "reason": "节点删除是高风险操作，需人工确认",
                "confidence": confidence,
                "source_count": source_count,
            }

        # 满足高置信 + 多源 → 自动应用
        if source_count >= self.high_confidence_sources and confidence >= self.confidence_threshold:
            return {
                "action": "auto_apply",
                "reason": (
                    f"数据源数量({source_count}) >= {self.high_confidence_sources} "
                    f"且置信度({confidence:.2f}) >= {self.confidence_threshold}"
                ),
                "confidence": confidence,
                "source_count": source_count,
            }
        return {
            "action": "human_review",
            "reason": (
                f"未达自动应用阈值 (需要 source_count>={self.high_confidence_sources} "
                f"且 confidence>={self.confidence_threshold})"
            ),
            "confidence": confidence,
            "source_count": source_count,
        }

    def route_batch(self, change_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量决策"""
        return [self.route(ev) for ev in change_events]


_singleton: Optional[AutoRouter] = None


def get_auto_router() -> AutoRouter:
    global _singleton
    if _singleton is None:
        _singleton = AutoRouter()
    return _singleton
