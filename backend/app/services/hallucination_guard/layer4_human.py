"""第四层 - 人工审核队列

将低置信度、新岗位、重大变更等需要人工介入的实体入队到 MySQL AuditLog 表。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.database import SessionLocal
from app.core.logger import log
from app.models.job_role import AuditLog


class HumanReviewQueue:
    """人工审核队列"""

    def enqueue(
        self,
        entity_type: str,
        entity_id: str,
        entity_data: Dict[str, Any],
        reason: str,
    ) -> Dict[str, Any]:
        """添加一个待审核实体"""
        record = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            entity_data=entity_data,
            reason=reason,
            status="pending",
        )
        try:
            with SessionLocal() as db:
                db.add(record)
                db.commit()
                db.refresh(record)
                log.info(f"入队审核: {entity_type}:{entity_id} ({reason})")
                return {
                    "id": record.id,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "status": "pending",
                    "created_at": str(record.created_at),
                }
        except Exception as e:
            log.warning(f"入队审核失败（DB 不可用）: {e}")
            return {
                "id": None,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "status": "pending",
                "reason": reason,
                "persisted": False,
            }

    def list_pending(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            with SessionLocal() as db:
                rows = db.query(AuditLog).filter(AuditLog.status == "pending")\
                    .order_by(AuditLog.id.desc()).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "entity_type": r.entity_type,
                    "entity_id": r.entity_id,
                    "entity_data": r.entity_data,
                    "reason": r.reason,
                    "status": r.status,
                    "created_at": str(r.created_at),
                }
                for r in rows
            ]
        except Exception as e:
            log.warning(f"读取审核队列失败: {e}")
            return []

    def approve(self, audit_id: int, reviewer: str, comment: Optional[str] = None) -> bool:
        return self._set_status(audit_id, "approved", reviewer, comment)

    def reject(self, audit_id: int, reviewer: str, comment: Optional[str] = None) -> bool:
        return self._set_status(audit_id, "rejected", reviewer, comment)

    def _set_status(
        self,
        audit_id: int,
        status: str,
        reviewer: str,
        comment: Optional[str],
    ) -> bool:
        from datetime import datetime
        try:
            with SessionLocal() as db:
                row = db.query(AuditLog).filter(AuditLog.id == audit_id).first()
                if not row:
                    return False
                row.status = status
                row.reviewed_by = reviewer
                row.reviewed_at = datetime.utcnow()
                row.review_comment = comment
                db.commit()
                log.info(f"审核 {audit_id} → {status} by {reviewer}")
                return True
        except Exception as e:
            log.error(f"审核操作失败: {e}")
            return False


_singleton: Optional[HumanReviewQueue] = None


def get_human_queue() -> HumanReviewQueue:
    global _singleton
    if _singleton is None:
        _singleton = HumanReviewQueue()
    return _singleton
