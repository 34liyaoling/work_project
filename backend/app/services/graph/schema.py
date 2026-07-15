"""Neo4j 图谱 Schema 定义

节点类型:
- JobRole: 岗位（如 "AI 工程师"）
- Skill: 技能（如 "Python"）
- Tool: 工具（如 "Docker"）
- Industry: 行业（如 "金融科技"）

关系类型:
- REQUIRES: 岗位 → 技能（必备/加分 + 权重 + 等级）
- INCLUDES: 技能 → 子技能/工具
- DEPENDS_ON: 技能 → 先修技能
- RELATED_TO: 技能 ↔ 技能（语义相关）
- SUBCATEGORY_OF: 技能 → 父技能
- OFTEN_USED_WITH: 技能 ↔ 技能（经常共现）
- BELONGS_TO: 技能/岗位 → 行业
"""
from __future__ import annotations

from typing import Dict, List


# 节点类型
NODE_LABELS = ["JobRole", "Skill", "Tool", "Industry"]


# 关系类型
RELATIONSHIP_TYPES = [
    "REQUIRES",
    "INCLUDES",
    "DEPENDS_ON",
    "RELATED_TO",
    "SUBCATEGORY_OF",
    "OFTEN_USED_WITH",
    "BELONGS_TO",
]


# 节点属性 Schema
NODE_PROPERTIES: Dict[str, Dict[str, str]] = {
    "JobRole": {
        "name": "string (unique)",
        "category": "string",
        "level": "string",
        "confidence": "float",
        "is_new": "boolean",
        "updated_at": "datetime",
        "description": "string",
    },
    "Skill": {
        "name": "string (unique)",
        "category": "string",
        "popularity": "float",
        "level": "string",
        "source": "string",
    },
    "Tool": {
        "name": "string (unique)",
        "category": "string",
        "vendor": "string",
    },
    "Industry": {
        "name": "string (unique)",
        "sector": "string",
    },
}


# 关系属性 Schema
REL_PROPERTIES: Dict[str, Dict[str, str]] = {
    "REQUIRES": {
        "kind": "string (required|preferred)",
        "weight": "float",
        "level_required": "string (基础|熟练|精通)",
    },
    "INCLUDES": {
        "weight": "float",
    },
    "DEPENDS_ON": {
        "strength": "float",
    },
    "RELATED_TO": {
        "score": "float",
    },
    "SUBCATEGORY_OF": {},
    "OFTEN_USED_WITH": {
        "cooccurrence": "int",
        "lift": "float",
    },
    "BELONGS_TO": {
        "weight": "float",
    },
}


# Cypher Schema 约束 / 索引
CONSTRAINT_QUERIES: List[str] = [
    "CREATE CONSTRAINT jobrole_name IF NOT EXISTS FOR (n:JobRole) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (n:Skill) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT tool_name IF NOT EXISTS FOR (n:Tool) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT industry_name IF NOT EXISTS FOR (n:Industry) REQUIRE n.name IS UNIQUE",
]

INDEX_QUERIES: List[str] = [
    "CREATE INDEX skill_category IF NOT EXISTS FOR (n:Skill) ON (n.category)",
    "CREATE INDEX jobrole_category IF NOT EXISTS FOR (n:JobRole) ON (n.category)",
    "CREATE INDEX jobrole_level IF NOT EXISTS FOR (n:JobRole) ON (n.level)",
    "CREATE INDEX skill_popularity IF NOT EXISTS FOR (n:Skill) ON (n.popularity)",
    "CREATE INDEX industry_sector IF NOT EXISTS FOR (n:Industry) ON (n.sector)",
]


GRAPH_SCHEMA: Dict[str, object] = {
    "node_labels": NODE_LABELS,
    "relationship_types": RELATIONSHIP_TYPES,
    "node_properties": NODE_PROPERTIES,
    "relationship_properties": REL_PROPERTIES,
    "constraint_queries": CONSTRAINT_QUERIES,
    "index_queries": INDEX_QUERIES,
}


def cypher_init_schema() -> List[str]:
    """生成完整的 schema 初始化 Cypher 语句"""
    return CONSTRAINT_QUERIES + INDEX_QUERIES
