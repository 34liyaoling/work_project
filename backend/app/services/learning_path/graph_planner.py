"""图谱驱动的学习顺序规划器

输入一组目标技能，查询 neo4j 中 DEPENDS_ON 关系，输出按学习阶段
（拓扑序）排列的技能列表。
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Sequence, Set

from app.core.logger import log
from app.core.neo4j_db import neo4j_client
from app.services.learning_path.dep_resolver import DepResolver


class GraphPlanner:
    """图谱学习顺序规划器"""

    def __init__(self, resolver: Optional[DepResolver] = None):
        self.resolver = resolver or DepResolver()

    def plan_stages(
        self,
        target_skills: Sequence[str],
    ) -> List[List[str]]:
        """对目标技能做拓扑分层（每个阶段一组互不依赖的技能）"""
        # 1. 收集依赖图（包含先修）
        graph: Dict[str, Set[str]] = defaultdict(set)  # node → prerequisites
        in_degree: Dict[str, int] = defaultdict(int)
        all_nodes: Set[str] = set(target_skills)

        for skill in target_skills:
            prereqs = self.resolver.resolve(skill)
            for p in prereqs:
                if p not in graph[skill]:
                    graph[skill].add(p)
                    in_degree[skill] += 1
                all_nodes.add(p)

        # 2. 拓扑分层（Kahn 算法）
        stages: List[List[str]] = []
        remaining = dict(in_degree)
        current_layer = sorted([s for s in target_skills if remaining.get(s, 0) == 0])
        visited: Set[str] = set()

        while current_layer:
            stages.append(current_layer)
            visited.update(current_layer)
            next_layer: Set[str] = set()
            for s in target_skills:
                if s in visited:
                    continue
                # 移除已访问的先修
                remaining[s] = sum(1 for p in graph[s] if p not in visited)
                if remaining[s] == 0:
                    next_layer.add(s)
            current_layer = sorted(next_layer)

        if len(visited) < len(target_skills):
            leftover = [s for s in target_skills if s not in visited]
            log.warning(f"图谱存在环或缺失依赖, 剩余技能并入最后一阶段: {leftover}")
            if leftover:
                stages.append(leftover)

        log.info(f"图谱规划阶段: {len(stages)} 层, {len(visited)} 节点已规划")
        return stages

    def fetch_dep_edges(self, skill_name: str) -> List[Dict[str, Any]]:
        """从 neo4j 中查询该技能的全部 DEPENDS_ON 关系"""
        driver = neo4j_client._driver  # type: ignore
        if not driver:
            return []
        try:
            with driver.session() as session:
                result = session.run(
                    "MATCH (a:Skill {name:$name})-[r:DEPENDS_ON]->(b:Skill) "
                    "RETURN b.name AS prereq, r.strength AS strength",
                    name=skill_name,
                )
                return [{"prereq": r["prereq"], "strength": r["strength"]} for r in result]
        except Exception as e:
            log.warning(f"查询依赖关系失败 {skill_name}: {e}")
            return []


_singleton: Optional[GraphPlanner] = None


def get_graph_planner() -> GraphPlanner:
    global _singleton
    if _singleton is None:
        _singleton = GraphPlanner()
    return _singleton
