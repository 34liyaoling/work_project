"""知识图谱构建（Neo4j）服务

包含 5 个子模块:
- schema: 图谱 Schema 定义
- batch_importer: 从清洗后数据批量导入
- incremental_updater: 增量更新
- query_service: Cypher 多维度查询
- domain_splitter: 按领域分库（性能优化）
"""
from app.services.graph.schema import GRAPH_SCHEMA, NODE_LABELS, RELATIONSHIP_TYPES
from app.services.graph.batch_importer import BatchImporter, get_batch_importer
from app.services.graph.incremental_updater import IncrementalUpdater, get_incremental_updater
from app.services.graph.query_service import GraphQueryService, get_graph_query_service
from app.services.graph.domain_splitter import DomainSplitter, get_domain_splitter


__all__ = [
    "GRAPH_SCHEMA",
    "NODE_LABELS",
    "RELATIONSHIP_TYPES",
    "BatchImporter",
    "IncrementalUpdater",
    "GraphQueryService",
    "DomainSplitter",
    "get_batch_importer",
    "get_incremental_updater",
    "get_graph_query_service",
    "get_domain_splitter",
]
