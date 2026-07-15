"""图谱增量更新服务

根据 evolution.change_classifier 输出的事件类型（added/removed/modified/weight_changed）
对 Neo4j 图谱做最小化更新。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.logger import log
from app.core.neo4j_db import neo4j_client


class IncrementalUpdater:
    """图谱增量更新器"""

    def apply_events(self, events: List[Dict[str, Any]], snapshot_id: Optional[str] = None) -> Dict[str, int]:
        """批量应用变更事件"""
        driver = neo4j_client._driver  # type: ignore
        counts = {"applied": 0, "skipped": 0, "errors": 0}
        if not driver:
            log.warning("Neo4j 未连接，增量更新进入 mock 模式")
            counts["applied"] = sum(1 for e in events if e.get("type") != "no_change")
            return counts

        for ev in events:
            try:
                self._apply_one(driver, ev, snapshot_id)
                counts["applied"] += 1
            except Exception as e:
                counts["errors"] += 1
                log.error(f"应用事件失败 {ev.get('type')} {ev.get('node_id')}: {e}")
        log.info(f"增量更新完成: {counts}")
        return counts

    def add_skill_to_role(
        self,
        role_name: str,
        skill_name: str,
        kind: str = "required",
        weight: float = 0.7,
        level: str = "熟练",
    ) -> bool:
        driver = neo4j_client._driver  # type: ignore
        if not driver:
            log.warning("Neo4j 未连接, mock add_skill_to_role")
            return True
        with driver.session() as session:
            session.run("MERGE (r:JobRole {name:$role})", role=role_name)
            session.run("MERGE (s:Skill {name:$skill})", skill=skill_name)
            session.run(
                "MATCH (r:JobRole {name:$role}),(s:Skill {name:$skill}) "
                "MERGE (r)-[rel:REQUIRES]->(s) "
                "SET rel.kind=$kind, rel.weight=$weight, rel.level_required=$level",
                role=role_name, skill=skill_name, kind=kind, weight=weight, level=level,
            )
        return True

    def remove_skill_from_role(self, role_name: str, skill_name: str) -> bool:
        driver = neo4j_client._driver  # type: ignore
        if not driver:
            return True
        with driver.session() as session:
            session.run(
                "MATCH (r:JobRole {name:$role})-[rel:REQUIRES]->(s:Skill {name:$skill}) "
                "DELETE rel",
                role=role_name, skill=skill_name,
            )
        return True

    def update_skill_weight(
        self,
        role_name: str,
        skill_name: str,
        new_weight: float,
    ) -> bool:
        driver = neo4j_client._driver  # type: ignore
        if not driver:
            return True
        with driver.session() as session:
            session.run(
                "MATCH (r:JobRole {name:$role})-[rel:REQUIRES]->(s:Skill {name:$skill}) "
                "SET rel.weight=$w",
                role=role_name, skill=skill_name, w=new_weight,
            )
        return True

    # ----------------- 内部 -----------------
    def _apply_one(self, driver, event: Dict[str, Any], snapshot_id: Optional[str]) -> None:
        et = event.get("type")
        node_id = event.get("node_id")
        detail = event.get("detail") or {}
        role = event.get("role_name") or detail.get("role") or "unknown"

        if et == "added":
            self.add_skill_to_role(
                role_name=role,
                skill_name=node_id,
                kind=detail.get("kind", "required"),
                weight=detail.get("weight", 0.7),
                level=detail.get("level", "熟练"),
            )
        elif et == "removed":
            self.remove_skill_from_role(role, node_id)
        elif et == "weight_changed":
            self.update_skill_weight(role, node_id, detail.get("new_weight", 0.5))
        elif et == "modified":
            self.update_skill_weight(role, node_id, detail.get("new_weight", 0.5))
        elif et == "no_change":
            pass


_singleton: Optional[IncrementalUpdater] = None


def get_incremental_updater() -> IncrementalUpdater:
    global _singleton
    if _singleton is None:
        _singleton = IncrementalUpdater()
    return _singleton
