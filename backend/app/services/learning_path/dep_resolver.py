"""先修技能依赖关系识别

优先从 neo4j 拉取 DEPENDS_ON 边，缺失时回退到内置规则库。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set

from app.core.logger import log
from app.core.neo4j_db import neo4j_client


# 内置先修关系（neo4j 不可用时使用）
BUILTIN_PREREQ: Dict[str, List[str]] = {
    "PyTorch": ["Python", "深度学习"],
    "TensorFlow": ["Python", "深度学习"],
    "LangChain": ["Python", "LLM"],
    "LlamaIndex": ["Python", "LLM"],
    "RAG": ["向量数据库", "Embedding", "LLM"],
    "Prompt Engineering": ["LLM"],
    "Kubernetes": ["Docker", "Linux"],
    "Docker": ["Linux"],
    "Spark": ["Scala", "Hadoop"],
    "Flink": ["Java", "Kafka"],
    "Kafka": ["Java", "ZooKeeper"],
    "深度学习": ["机器学习"],
    "机器学习": ["Python", "统计学"],
    "计算机视觉": ["深度学习"],
    "自然语言处理": ["深度学习"],
    "大语言模型": ["深度学习", "Transformer"],
    "Transformer": ["深度学习"],
    "LLM": ["深度学习", "Transformer"],
    "Function Calling": ["LLM"],
    "Agent": ["Function Calling", "LLM"],
    "MCP": ["LLM"],
}


class DepResolver:
    """先修依赖解析器"""

    def resolve(self, skill_name: str) -> List[str]:
        """获取某技能的全部先修（去重）"""
        result: Set[str] = set()
        # 1. neo4j
        for p in self._from_graph(skill_name):
            result.add(p)
        # 2. 规则库
        for p in BUILTIN_PREREQ.get(skill_name, []):
            result.add(p)
        return sorted(result)

    def resolve_batch(self, skills: Sequence[str]) -> Dict[str, List[str]]:
        return {s: self.resolve(s) for s in skills or []}

    def _from_graph(self, skill_name: str) -> List[str]:
        driver = neo4j_client._driver  # type: ignore
        if not driver:
            return []
        try:
            with driver.session() as session:
                rows = session.run(
                    "MATCH (a:Skill {name:$name})-[r:DEPENDS_ON]->(b:Skill) "
                    "RETURN b.name AS prereq",
                    name=skill_name,
                )
                return [r["prereq"] for r in rows if r.get("prereq")]
        except Exception as e:
            log.warning(f"图谱依赖查询失败 {skill_name}: {e}")
            return []


_singleton: Optional[DepResolver] = None


def get_dep_resolver() -> DepResolver:
    global _singleton
    if _singleton is None:
        _singleton = DepResolver()
    return _singleton
