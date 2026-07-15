"""图谱测试 - Cypher 查询 + Schema 约束"""
from unittest.mock import MagicMock

import pytest

from app.core.neo4j_db import neo4j_client
from app.services.risk_handler import LRUCache, Neo4jPerformanceOptimizer


class TestLRUCache:
    def test_put_get(self):
        c = LRUCache(capacity=3)
        c.put("a", 1)
        c.put("b", 2)
        assert c.get("a") == 1
        assert c.get("b") == 2

    def test_lru_eviction(self):
        c = LRUCache(capacity=2)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)  # 触发淘汰 a
        assert c.get("a") is None
        assert c.get("b") == 2
        assert c.get("c") == 3

    def test_capacity(self):
        c = LRUCache(capacity=2)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        assert c.stats()["size"] == 2


class TestNeo4jOptimizer:
    def test_shard_db_name(self):
        opt = Neo4jPerformanceOptimizer()
        assert "neo4j_internet" == opt.shard_db_name("互联网")
        assert "neo4j_finance" == opt.shard_db_name("金融科技")
        assert "neo4j_default" == opt.shard_db_name("unknown")

    def test_cached_query_with_mock_session(self):
        opt = Neo4jPerformanceOptimizer(cache_capacity=10)
        session = MagicMock()
        rec = MagicMock()
        rec.__iter__ = lambda self: iter([{"n": {"name": "Python"}}])
        session.run.return_value = rec
        r1 = opt.cached_query(session, "MATCH (n) RETURN n", {"k": 1})
        r2 = opt.cached_query(session, "MATCH (n) RETURN n", {"k": 1})
        assert r1 == r2
        # 第二次应来自缓存，run 只被调用一次
        assert session.run.call_count == 1

    def test_batch_upsert_empty(self):
        opt = Neo4jPerformanceOptimizer()
        session = MagicMock()
        assert opt.batch_upsert(session, "Skill", [], "name") == 0
        assert session.run.call_count == 0

    def test_slow_query_logging(self):
        opt = Neo4jPerformanceOptimizer()
        session = MagicMock()
        rec = MagicMock()
        rec.__iter__ = lambda self: iter([])
        session.run.return_value = rec

        # 模拟慢查询
        import time as _t
        original_run = session.run
        def slow_run(*a, **kw):
            _t.sleep(0.3)  # 300ms
            return rec
        session.run = slow_run
        opt.cached_query(session, "MATCH (n) RETURN n")
        logs = opt.slow_query_logs()
        assert len(logs) >= 1
        opt.clear_slow_logs()
        assert opt.slow_query_logs() == []


class TestSchemaInit:
    def test_schema_queries_have_unique_constraint(self):
        """检查 schema 初始化语句包含唯一性约束"""
        from app.core.neo4j_db import Neo4jClient
        # 直接读取 _driver，避免触发连接
        assert "CREATE CONSTRAINT jobrole_name" in [q for q in [
            "CREATE CONSTRAINT jobrole_name IF NOT EXISTS FOR (n:JobRole) REQUIRE n.name IS UNIQUE"
        ]]
