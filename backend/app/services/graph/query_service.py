"""Cypher 多维度查询服务

支持按技术栈 / 级别 / 领域 / 行业 等多维度查询岗位及其技能图谱。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from app.core.logger import log
from app.core.neo4j_db import neo4j_client


class GraphQueryService:
    """图谱查询服务"""

    def query_jobs_by_skills(
        self,
        skills: Sequence[str],
        level: Optional[str] = None,
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """按技能组合反查匹配的岗位（按命中数排序）"""
        if not skills:
            return []
        cypher = (
            "MATCH (r:JobRole)-[rel:REQUIRES]->(s:Skill) "
            "WHERE s.name IN $skills "
            + ("AND r.level = $level " if level else "")
            + "WITH r, sum(rel.weight) AS score, count(s) AS hits "
            "RETURN r.name AS role, r.category AS category, r.level AS level, "
            "       score, hits "
            "ORDER BY score DESC LIMIT $top_k"
        )
        params: Dict[str, Any] = {"skills": list(skills), "top_k": int(top_k)}
        if level:
            params["level"] = level
        return self._run(cypher, params)

    def query_skills_by_role(self, role_name: str) -> Dict[str, Any]:
        """查询某岗位的全部技能（必备/加分分组）"""
        cypher = (
            "MATCH (r:JobRole {name:$name})-[rel:REQUIRES]->(s:Skill) "
            "RETURN s.name AS skill, s.category AS category, rel.kind AS kind, "
            "       rel.weight AS weight, rel.level_required AS level "
            "ORDER BY rel.kind, rel.weight DESC"
        )
        rows = self._run(cypher, {"name": role_name})
        result: Dict[str, Any] = {"required": [], "preferred": []}
        for r in rows:
            target = "required" if r.get("kind") == "required" else "preferred"
            result[target].append(r)
        return result

    def query_jobs_by_industry(self, industry: str, top_k: int = 50) -> List[Dict[str, Any]]:
        cypher = (
            "MATCH (r:JobRole)-[rel:BELONGS_TO]->(i:Industry {name:$industry}) "
            "RETURN r.name AS role, r.category AS category, r.level AS level, rel.weight AS weight "
            "ORDER BY rel.weight DESC LIMIT $top_k"
        )
        return self._run(cypher, {"industry": industry, "top_k": int(top_k)})

    def query_skill_dependencies(self, skill_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """查询某技能的先修与被依赖关系"""
        prereq = self._run(
            "MATCH (a:Skill {name:$name})-[r:DEPENDS_ON]->(b:Skill) "
            "RETURN b.name AS skill, r.strength AS strength",
            {"name": skill_name},
        )
        downstream = self._run(
            "MATCH (a:Skill)-[r:DEPENDS_ON]->(b:Skill {name:$name}) "
            "RETURN a.name AS skill, r.strength AS strength",
            {"name": skill_name},
        )
        return {"prerequisites": prereq, "downstream": downstream}

    def query_related_skills(self, skill_name: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """按 OFTEN_USED_WITH / RELATED_TO 查询相关技能"""
        cypher = (
            "MATCH (s:Skill {name:$name})-[r:OFTEN_USED_WITH|RELATED_TO]-(o:Skill) "
            "RETURN o.name AS skill, type(r) AS rel, coalesce(r.lift, r.score, 0.0) AS score "
            "ORDER BY score DESC LIMIT $top_k"
        )
        return self._run(cypher, {"name": skill_name, "top_k": int(top_k)})

    def stats(self) -> Dict[str, int]:
        """图谱统计信息"""
        result: Dict[str, int] = {}
        for label in ("JobRole", "Skill", "Tool", "Industry"):
            rows = self._run(f"MATCH (n:{label}) RETURN count(n) AS cnt", {})
            result[label] = int(rows[0]["cnt"]) if rows else 0
        return result

    # ----------------- 内部 -----------------
    def _run(self, cypher: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        driver = neo4j_client._driver  # type: ignore
        if not driver:
            log.warning("Neo4j 未连接, query_service 进入 mock 模式")
            return []
        try:
            with driver.session() as session:
                result = session.run(cypher, **params)
                return [dict(record) for record in result]
        except Exception as e:
            log.error(f"Cypher 执行失败: {e}\nCYPHER: {cypher}")
            return []


_singleton: Optional[GraphQueryService] = None


def get_graph_query_service() -> GraphQueryService:
    global _singleton
    if _singleton is None:
        _singleton = GraphQueryService()
    return _singleton
