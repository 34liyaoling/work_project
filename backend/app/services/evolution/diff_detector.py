"""增量采集与差异检测

将新采集的 JD 集合 / 技能组合与现有图谱（neo4j + MySQL 岗位卡片）对比，
输出 diff 报告（新增/删除/修改/权重变化/不变）。
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from app.core.logger import log


class DiffDetector:
    """差异检测器"""

    def detect_skill_diff(
        self,
        existing_role: Dict[str, Any],
        incoming_role: Dict[str, Any],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """对比既有岗位定义 vs 新数据产生的岗位定义

        :return: {"added":[...],"removed":[...],"modified":[...],"weight_changed":[...]}
        """
        existing = self._skill_to_map(existing_role.get("required_skills", []))
        incoming = self._skill_to_map(incoming_role.get("required_skills", []))

        added = [
            {"skill": s, "level": meta.get("level"), "weight": meta.get("weight")}
            for s, meta in incoming.items()
            if s not in existing
        ]
        removed = [
            {"skill": s, "level": meta.get("level"), "weight": meta.get("weight")}
            for s, meta in existing.items()
            if s not in incoming
        ]
        modified: List[Dict[str, Any]] = []
        weight_changed: List[Dict[str, Any]] = []
        for s, new_meta in incoming.items():
            if s in existing:
                old_meta = existing[s]
                if new_meta.get("level") != old_meta.get("level"):
                    modified.append({
                        "skill": s,
                        "old_level": old_meta.get("level"),
                        "new_level": new_meta.get("level"),
                    })
                if abs((new_meta.get("weight") or 0) - (old_meta.get("weight") or 0)) > 0.05:
                    weight_changed.append({
                        "skill": s,
                        "old_weight": old_meta.get("weight"),
                        "new_weight": new_meta.get("weight"),
                        "delta": round((new_meta.get("weight") or 0) - (old_meta.get("weight") or 0), 3),
                    })
        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "weight_changed": weight_changed,
        }

    def detect_jd_diff(
        self,
        existing_jd_ids: Sequence[str],
        new_jd_records: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """检测增量 JD 集合差异

        :return: {"new_jds": [...], "skipped_ids": [...], "new_skills": Counter}
        """
        existing_set: Set[str] = set(existing_jd_ids or [])
        new_skills: Counter = Counter()
        new_jds: List[Dict[str, Any]] = []
        skipped: List[str] = []
        for jd in new_jd_records or []:
            jd_id = jd.get("jd_id") or jd.get("id")
            if not jd_id:
                continue
            if jd_id in existing_set:
                skipped.append(jd_id)
                continue
            new_jds.append(jd)
            for s in jd.get("skills", []) or []:
                new_skills[s] += 1
        log.info(f"增量检测: 新增 JD {len(new_jds)} / 跳过 {len(skipped)} / 新增技能种类 {len(new_skills)}")
        return {
            "new_jds": new_jds,
            "skipped_ids": skipped,
            "new_skills": new_skills,
        }

    # ----------------- 内部 -----------------
    @staticmethod
    def _skill_to_map(skills: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        m: Dict[str, Dict[str, Any]] = {}
        for item in skills or []:
            name = (item.get("skill") or "").strip().lower()
            if not name:
                continue
            m[name] = item
        return m


_singleton: Optional[DiffDetector] = None


def get_diff_detector() -> DiffDetector:
    global _singleton
    if _singleton is None:
        _singleton = DiffDetector()
    return _singleton
