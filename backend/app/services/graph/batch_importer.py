"""图谱批量导入服务

从清洗后的结构化数据（JobRoleCard + 技能列表）批量写入 Neo4j。
支持事务批处理、失败回滚与导入统计。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from app.core.logger import log
from app.core.neo4j_db import neo4j_client
from app.services.graph.schema import cypher_init_schema


# 节点合并 Cypher
_MERGE_JOBROLE = """
MERGE (r:JobRole {name: $name})
ON CREATE SET r.created_at = datetime()
SET r.category = $category,
    r.level = $level,
    r.confidence = $confidence,
    r.is_new = $is_new,
    r.description = $description,
    r.updated_at = datetime()
RETURN r
"""

_MERGE_SKILL = """
MERGE (s:Skill {name: $name})
ON CREATE SET s.created_at = datetime()
SET s.category = $category,
    s.popularity = $popularity,
    s.level = $level,
    s.source = $source
RETURN s
"""

_MERGE_INDUSTRY = """
MERGE (i:Industry {name: $name})
ON CREATE SET i.created_at = datetime()
SET i.sector = $sector
RETURN i
"""

_MERGE_REQUIRES = """
MATCH (r:JobRole {name: $role}), (s:Skill {name: $skill})
MERGE (r)-[rel:REQUIRES]->(s)
SET rel.kind = $kind,
    rel.weight = $weight,
    rel.level_required = $level
RETURN rel
"""

_MERGE_BELONGS = """
MATCH (r:JobRole {name: $role}), (i:Industry {name: $industry})
MERGE (r)-[rel:BELONGS_TO]->(i)
SET rel.weight = $weight
RETURN rel
"""

_MERGE_DEPENDS = """
MATCH (a:Skill {name: $from}), (b:Skill {name: $to})
MERGE (a)-[rel:DEPENDS_ON]->(b)
SET rel.strength = $strength
RETURN rel
"""


class BatchImporter:
    """图谱批量导入器"""

    def __init__(self):
        self.stats = {"jobroles": 0, "skills": 0, "industries": 0, "edges": 0, "errors": 0}

    def ensure_schema(self) -> None:
        """确保约束与索引存在"""
        driver = neo4j_client._driver  # type: ignore
        if not driver:
            log.warning("Neo4j 未连接，跳过 schema 创建")
            return
        try:
            with driver.session() as session:
                for q in cypher_init_schema():
                    session.run(q)
            log.info("Graph schema 已确保存在")
        except Exception as e:
            log.error(f"Schema 创建失败: {e}")

    def import_job_roles(
        self,
        job_roles: Iterable[Dict[str, Any]],
        batch_size: int = 200,
    ) -> Dict[str, int]:
        """批量导入岗位 + 必备/加分技能 + 行业归属

        :param job_roles: 岗位定义列表，每项含 required_skills / preferred_skills / industry
        """
        self.ensure_schema()
        driver = neo4j_client._driver  # type: ignore
        if not driver:
            log.warning("Neo4j 未连接，进入 mock 模式，仅做计数")
            return self._mock_import(job_roles)

        for role in job_roles:
            try:
                self._import_one(driver, role)
            except Exception as e:
                self.stats["errors"] += 1
                log.error(f"导入岗位 {role.get('name')} 失败: {e}")
        log.info(f"批量导入完成: {self.stats}")
        return dict(self.stats)

    # ----------------- 内部 -----------------
    def _import_one(self, driver, role: Dict[str, Any]) -> None:
        with driver.session() as session:
            session.run(_MERGE_JOBROLE, **{
                "name": role.get("name", "unknown"),
                "category": role.get("category", "其它"),
                "level": role.get("level", "中级"),
                "confidence": float(role.get("confidence", 0.7)),
                "is_new": bool(role.get("is_new", False)),
                "description": role.get("description", ""),
            })
            self.stats["jobroles"] += 1
            role_name = role.get("name", "unknown")

            for skill in role.get("required_skills", []) or []:
                self._merge_skill_node(session, skill, kind="required", role_name=role_name)
            for skill in role.get("preferred_skills", []) or []:
                self._merge_skill_node(session, skill, kind="preferred", role_name=role_name)

            # 行业归属
            for industry in role.get("industries", []) or []:
                session.run(_MERGE_INDUSTRY, name=industry, sector=role.get("category", "其它"))
                self.stats["industries"] += 1
                session.run(_MERGE_BELONGS, role=role_name, industry=industry, weight=0.8)
                self.stats["edges"] += 1

    def _merge_skill_node(self, session, skill: Dict[str, Any], kind: str, role_name: str) -> None:
        name = (skill.get("skill") or "").strip()
        if not name:
            return
        session.run(_MERGE_SKILL, **{
            "name": name,
            "category": skill.get("category", "通用"),
            "popularity": float(skill.get("popularity", 0.5)),
            "level": skill.get("level", "熟练"),
            "source": skill.get("source", "imported"),
        })
        self.stats["skills"] += 1
        session.run(_MERGE_REQUIRES, **{
            "role": role_name,
            "skill": name,
            "kind": kind,
            "weight": float(skill.get("weight", 0.5)),
            "level": skill.get("level", "熟练"),
        })
        self.stats["edges"] += 1

    def _mock_import(self, job_roles: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        """无 Neo4j 连接时的 mock 统计"""
        for role in job_roles:
            self.stats["jobroles"] += 1
            self.stats["skills"] += len(role.get("required_skills", []) or [])
            self.stats["skills"] += len(role.get("preferred_skills", []) or [])
            self.stats["industries"] += len(role.get("industries", []) or [])
            self.stats["edges"] += (
                len(role.get("required_skills", []) or [])
                + len(role.get("preferred_skills", []) or [])
                + len(role.get("industries", []) or [])
            )
        return dict(self.stats)


_singleton: Optional[BatchImporter] = None


def get_batch_importer() -> BatchImporter:
    global _singleton
    if _singleton is None:
        _singleton = BatchImporter()
    return _singleton
