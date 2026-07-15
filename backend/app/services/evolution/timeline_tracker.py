"""变更类型标注与时间线追踪

将变更事件按时间线归档到 MySQL GraphChangeLog 表，输出可被前端消费的时间线序列。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.database import SessionLocal
from app.core.logger import log
from app.models.job_role import GraphChangeLog


class TimelineTracker:
    """变更时间线追踪器"""

    def record(
        self,
        change_type: str,
        node_type: str,
        node_id: str,
        node_name: Optional[str] = None,
        change_detail: Optional[Dict[str, Any]] = None,
        confidence: float = 0.0,
        source_count: int = 1,
        is_auto_applied: bool = False,
        snapshot_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """记录一条变更事件"""
        record = GraphChangeLog(
            change_type=change_type,
            node_type=node_type,
            node_id=node_id,
            node_name=node_name or node_id,
            change_detail=change_detail or {},
            confidence=confidence,
            source_count=source_count,
            is_auto_applied=1 if is_auto_applied else 0,
            snapshot_id=snapshot_id,
        )
        try:
            with SessionLocal() as db:
                db.add(record)
                db.commit()
                db.refresh(record)
                log.info(f"时间线记录: {change_type} {node_type}:{node_id} (conf={confidence:.2f})")
                return {
                    "id": record.id,
                    "change_type": change_type,
                    "node_id": node_id,
                    "created_at": str(record.created_at),
                }
        except Exception as e:
            log.warning(f"时间线记录失败（DB 不可用）: {e}")
            return {
                "id": None,
                "change_type": change_type,
                "node_id": node_id,
                "created_at": datetime.utcnow().isoformat(),
                "persisted": False,
            }

    def list_timeline(
        self,
        node_id: Optional[str] = None,
        change_type: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """读取时间线，可按节点或类型过滤"""
        try:
            with SessionLocal() as db:
                q = db.query(GraphChangeLog)
                if node_id:
                    q = q.filter(GraphChangeLog.node_id == node_id)
                if change_type:
                    q = q.filter(GraphChangeLog.change_type == change_type)
                rows = q.order_by(GraphChangeLog.id.desc()).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "change_type": r.change_type,
                    "node_type": r.node_type,
                    "node_id": r.node_id,
                    "node_name": r.node_name,
                    "change_detail": r.change_detail,
                    "confidence": r.confidence,
                    "source_count": r.source_count,
                    "is_auto_applied": bool(r.is_auto_applied),
                    "snapshot_id": r.snapshot_id,
                    "created_at": str(r.created_at),
                }
                for r in rows
            ]
        except Exception as e:
            log.warning(f"时间线读取失败: {e}")
            return []

    def annotate(self, change_event: Dict[str, Any]) -> Dict[str, Any]:
        """为单条变更事件打上时间戳与标签（无需 DB）"""
        return {
            **change_event,
            "annotated_at": datetime.utcnow().isoformat(),
            "severity": self._severity(change_event),
        }

    @staticmethod
    def _severity(ev: Dict[str, Any]) -> str:
        t = ev.get("type")
        if t in ("added", "removed"):
            return "high"
        if t == "modified":
            return "medium"
        if t == "weight_changed":
            delta = abs((ev.get("detail") or {}).get("delta", 0) or 0)
            return "high" if delta > 0.2 else "low"
        return "info"


_singleton: Optional[TimelineTracker] = None


def get_timeline_tracker() -> TimelineTracker:
    global _singleton
    if _singleton is None:
        _singleton = TimelineTracker()
    return _singleton
