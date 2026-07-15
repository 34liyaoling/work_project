"""变更分类

将差异检测结果分类为:
- added: 全新节点
- removed: 节点消失
- modified: 属性变更
- weight_changed: 权重变化
- no_change: 无变化
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.core.logger import log


class ChangeClassifier:
    """变更分类器"""

    CHANGE_TYPES = ("added", "removed", "modified", "weight_changed", "no_change")

    def classify(self, diff: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """将 diff 字典展开为变更事件列表

        :return: [{"type":"added", "node_type":"skill", "node_id":"python", "detail":{...}}]
        """
        events: List[Dict[str, Any]] = []

        for item in diff.get("added", []):
            events.append(self._event("added", "skill", item.get("skill"), {
                "level": item.get("level"),
                "weight": item.get("weight"),
            }))

        for item in diff.get("removed", []):
            events.append(self._event("removed", "skill", item.get("skill"), {
                "level": item.get("level"),
                "weight": item.get("weight"),
            }))

        for item in diff.get("modified", []):
            events.append(self._event("modified", "skill", item.get("skill"), {
                "old_level": item.get("old_level"),
                "new_level": item.get("new_level"),
            }))

        for item in diff.get("weight_changed", []):
            events.append(self._event("weight_changed", "skill", item.get("skill"), {
                "old_weight": item.get("old_weight"),
                "new_weight": item.get("new_weight"),
                "delta": item.get("delta"),
            }))

        if not events:
            events.append(self._event("no_change", "skill", None, {}))
        log.info(f"变更分类: {len(events)} 个事件")
        return events

    @staticmethod
    def _event(change_type: str, node_type: str, node_id: Any, detail: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": change_type,
            "node_type": node_type,
            "node_id": node_id,
            "detail": detail,
        }


_singleton = None


def get_change_classifier() -> ChangeClassifier:
    global _singleton
    if _singleton is None:
        _singleton = ChangeClassifier()
    return _singleton
