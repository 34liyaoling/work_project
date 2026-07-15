"""Neo4j 图数据库连接"""
from neo4j import GraphDatabase
from typing import Optional

from app.core.config import settings
from app.core.logger import log


class Neo4jClient:
    """Neo4j 客户端封装"""

    def __init__(self):
        self._driver = None
        self._connect()

    def _connect(self):
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=30
            )
            # 验证连接
            with self._driver.session() as session:
                session.run("RETURN 1")
            log.info("Neo4j 连接成功")
        except Exception as e:
            log.error(f"Neo4j 连接失败: {e}")
            self._driver = None

    def get_session(self):
        if not self._driver:
            self._connect()
        return self._driver.session() if self._driver else None

    def close(self):
        if self._driver:
            self._driver.close()
            log.info("Neo4j 连接关闭")

    def init_schema(self):
        """初始化图谱Schema约束与索引"""
        if not self._driver:
            log.warning("Neo4j 未连接，跳过Schema初始化")
            return
        schema_queries = [
            # 节点唯一性约束
            "CREATE CONSTRAINT jobrole_name IF NOT EXISTS FOR (n:JobRole) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (n:Skill) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT tool_name IF NOT EXISTS FOR (n:Tool) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT industry_name IF NOT EXISTS FOR (n:Industry) REQUIRE n.name IS UNIQUE",
            # 索引
            "CREATE INDEX skill_category IF NOT EXISTS FOR (n:Skill) ON (n.category)",
            "CREATE INDEX jobrole_category IF NOT EXISTS FOR (n:JobRole) ON (n.category)",
            "CREATE INDEX skill_popularity IF NOT EXISTS FOR (n:Skill) ON (n.popularity)",
        ]
        try:
            with self._driver.session() as session:
                for q in schema_queries:
                    session.run(q)
            log.info("Neo4j Schema 初始化完成")
        except Exception as e:
            log.error(f"Neo4j Schema 初始化失败: {e}")


neo4j_client = Neo4jClient()
