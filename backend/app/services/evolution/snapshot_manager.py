"""图谱版本快照保存与回滚

将图谱当前状态（节点+边）序列化为 JSON 持久化至 MySQL GraphSnapshot 表，
支持按 snapshot_id 加载与回滚（数据回填，不直接修改 neo4j）。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from app.core.logger import log
from app.core.database import SessionLocal
from app.models.job_role import GraphSnapshot


class SnapshotManager:
    """图谱快照管理器"""

    def create_snapshot(
        self,
        description: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        snapshot_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """保存图谱快照

        :param description: 快照描述
        :param nodes: 节点列表 [{id, label, props}]
        :param edges: 边列表 [{source, target, type, props}]
        :return: 快照元数据
        """
        snap_id = snapshot_id or f"snap_{uuid.uuid4().hex[:12]}"
        payload = {"nodes": nodes, "edges": edges}
        record = GraphSnapshot(
            snapshot_id=snap_id,
            description=description,
            node_count=len(nodes),
            edge_count=len(edges),
            snapshot_data=payload,
        )
        try:
            with SessionLocal() as db:
                db.add(record)
                db.commit()
                db.refresh(record)
        except Exception as e:
            log.error(f"快照保存失败: {e}")
            # 即使数据库不可用也返回 ID
            return {
                "snapshot_id": snap_id,
                "description": description,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "persisted": False,
            }
        log.info(f"快照已保存: {snap_id} (节点={len(nodes)} 边={len(edges)})")
        return {
            "snapshot_id": snap_id,
            "description": description,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "persisted": True,
            "created_at": getattr(record, "created_at", None),
        }

    def list_snapshots(self, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            with SessionLocal() as db:
                rows = db.query(GraphSnapshot).order_by(GraphSnapshot.id.desc()).limit(limit).all()
            return [
                {
                    "snapshot_id": r.snapshot_id,
                    "description": r.description,
                    "node_count": r.node_count,
                    "edge_count": r.edge_count,
                    "created_at": str(r.created_at),
                }
                for r in rows
            ]
        except Exception as e:
            log.warning(f"快照列表读取失败: {e}")
            return []

    def load_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 加载快照数据"""
        try:
            with SessionLocal() as db:
                row = db.query(GraphSnapshot).filter(GraphSnapshot.snapshot_id == snapshot_id).first()
            if not row:
                return None
            data = row.snapshot_data
            if isinstance(data, str):
                data = json.loads(data)
            return {
                "snapshot_id": row.snapshot_id,
                "description": row.description,
                "node_count": row.node_count,
                "edge_count": row.edge_count,
                "data": data,
            }
        except Exception as e:
            log.error(f"快照加载失败 {snapshot_id}: {e}")
            return None

    def rollback(self, snapshot_id: str) -> Dict[str, Any]:
        """回滚到指定快照，返回图谱数据（不直接执行 neo4j 写入）

        :return: {"snapshot_id":..., "nodes":[...], "edges":[...]}
        """
        snap = self.load_snapshot(snapshot_id)
        if not snap:
            return {"error": f"snapshot {snapshot_id} not found"}
        log.warning(f"回滚请求: snapshot={snapshot_id} 节点={snap['node_count']}")
        return {
            "snapshot_id": snapshot_id,
            "nodes": snap["data"].get("nodes", []),
            "edges": snap["data"].get("edges", []),
        }


_singleton: Optional[SnapshotManager] = None


def get_snapshot_manager() -> SnapshotManager:
    global _singleton
    if _singleton is None:
        _singleton = SnapshotManager()
    return _singleton
