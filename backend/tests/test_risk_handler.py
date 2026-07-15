"""RiskHandler 单元测试"""
import time

import pytest

from app.services.risk_handler import (
    AntiCrawlStrategy,
    LLMStabilityGuard,
    Neo4jPerformanceOptimizer,
    PriorityScheduler,
    ProxyPool,
    RateLimiter,
    RiskHandler,
    UserAgentRotator,
    PRIORITY_NEW_ROLE_DISCOVERY,
    PRIORITY_GRAPH_UPDATE,
    PRIORITY_MATCHING,
    PRIORITY_RESUME_PARSE,
)


class TestProxyPool:
    def test_default_proxies(self):
        p = ProxyPool()
        assert p.next() is not None

    def test_rotate(self):
        p = ProxyPool(["http://a", "http://b", "http://c"])
        first = p.next()
        rotated = p.rotate()
        assert first != rotated


class TestUserAgentRotator:
    def test_ua_pool_size(self):
        r = UserAgentRotator()
        assert len(r.POOL) >= 3

    def test_rotate_distinct(self):
        r = UserAgentRotator()
        seen = {r.next() for _ in range(3)}
        assert len(seen) >= 2


class TestRateLimiter:
    def test_wait(self):
        rl = RateLimiter(min_interval_s=0.05, max_interval_s=0.1)
        s = rl.wait()
        assert s == 0.0  # 第一次调用不等待
        s2 = rl.wait()
        assert s2 > 0.0  # 第二次需要等待


class TestAntiCrawlStrategy:
    def test_build_headers(self):
        ac = AntiCrawlStrategy()
        h = ac.build_headers()
        assert "User-Agent" in h
        assert "Accept" in h


class TestLLMStabilityGuard:
    def test_call_success(self):
        guard = LLMStabilityGuard(max_retries=2)
        result = guard.call(
            caller=lambda: '{"skills": ["Python"]}',
            schema={
                "type": "object",
                "required": ["skills"],
                "properties": {"skills": {"type": "array"}},
            },
        )
        assert result.success is True
        assert result.data["skills"] == ["Python"]

    def test_call_with_retry_then_success(self):
        guard = LLMStabilityGuard(max_retries=3, backoff_base=1.0)
        attempts = {"n": 0}

        def caller():
            attempts["n"] += 1
            if attempts["n"] < 2:
                return "not-json"
            return '{"skills": ["ML"]}'

        result = guard.call(caller=caller)
        assert result.success is True
        assert attempts["n"] == 2

    def test_call_fallback_to_mock(self):
        guard = LLMStabilityGuard(max_retries=2, enable_mock_fallback=True)
        result = guard.call(
            caller=lambda: "永远非json",
            mock_fn=lambda: {"mock": True, "skills": []},
        )
        assert result.success is True
        assert result.data["mock"] is True

    def test_call_full_failure(self):
        guard = LLMStabilityGuard(max_retries=1, enable_mock_fallback=False)
        result = guard.call(caller=lambda: "not json")
        assert result.success is False


class TestPriorityScheduler:
    def test_priority_order(self):
        s = PriorityScheduler()
        order = []

        s.add("A", lambda: order.append("A"), priority=PRIORITY_MATCHING)
        s.add("B", lambda: order.append("B"), priority=PRIORITY_NEW_ROLE_DISCOVERY)
        s.add("C", lambda: order.append("C"), priority=PRIORITY_RESUME_PARSE)
        s.add("D", lambda: order.append("D"), priority=PRIORITY_GRAPH_UPDATE)

        s.drain()
        # B (10) -> D (20) -> A (30) -> C (40)
        assert order == ["B", "D", "A", "C"]

    def test_size(self):
        s = PriorityScheduler()
        s.add("x", lambda: None, priority=10)
        s.add("y", lambda: None, priority=20)
        assert s.size() == 2


class TestRiskHandlerAggregate:
    def test_aggregate_init(self):
        rh = RiskHandler()
        assert isinstance(rh.anti_crawl, AntiCrawlStrategy)
        assert isinstance(rh.llm_guard, LLMStabilityGuard)
        assert isinstance(rh.neo4j_opt, Neo4jPerformanceOptimizer)
        assert isinstance(rh.scheduler, PriorityScheduler)
