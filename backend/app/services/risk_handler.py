"""风险应对与性能优化模块

包含：
- AntiCrawlStrategy: 反爬策略（代理池、UA 轮换、频率控制、Playwright 模拟真人）
- LLMStabilityGuard: 大模型稳定性保障（Schema 校验、Regex 校验、自动重试、Mock 降级）
- Neo4jPerformanceOptimizer: Neo4j 性能优化（分库策略、查询缓存、批量写入、慢查询日志）
- PriorityScheduler: 任务优先级调度
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from app.core.logger import log


# ===========================================================
# 1. 反爬策略
# ===========================================================
class ProxyPool:
    """简单的代理池：环形选择可用代理"""

    def __init__(self, proxies: Optional[List[str]] = None):
        # 示例代理列表（生产环境应来自代理供应商接口）
        self._proxies: deque = deque(proxies or [
            "http://proxy1.example.com:8080",
            "http://proxy2.example.com:8080",
            "http://proxy3.example.com:8080",
        ])

    def add(self, proxy: str) -> None:
        if proxy and proxy not in self._proxies:
            self._proxies.append(proxy)

    def next(self) -> Optional[str]:
        if not self._proxies:
            return None
        return self._proxies[0]  # 简单返回头部，下游可标记失败后轮转

    def rotate(self) -> Optional[str]:
        if not self._proxies:
            return None
        self._proxies.rotate(-1)
        return self._proxies[0]

    def all(self) -> List[str]:
        return list(self._proxies)


class UserAgentRotator:
    """UA 轮换器"""

    POOL = [
        # Chrome / Win
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        # Chrome / Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        # Firefox / Win
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
        # Safari / Mac
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        # Edge / Win
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
    ]

    def __init__(self, custom: Optional[List[str]] = None):
        self._pool = list(custom) if custom else self.POOL
        self._idx = 0

    def next(self) -> str:
        ua = self._pool[self._idx % len(self._pool)]
        self._idx += 1
        return ua


class RateLimiter:
    """请求频率控制器：保证两次请求之间至少间隔 [min_s, max_s]"""

    def __init__(self, min_interval_s: float = 2.0, max_interval_s: float = 5.0):
        self.min_s = float(min_interval_s)
        self.max_s = float(max_interval_s)
        self._last_call_ts: float = 0.0
        self._lock = threading.Lock()

    def wait(self) -> float:
        """同步等待，返回实际 sleep 时长"""
        with self._lock:
            now = time.time()
            if self._last_call_ts == 0.0:
                self._last_call_ts = now
                return 0.0
            elapsed = now - self._last_call_ts
            target = random.uniform(self.min_s, self.max_s)
            sleep_for = max(0.0, target - elapsed)
            if sleep_for > 0:
                time.sleep(sleep_for)
            self._last_call_ts = time.time()
            return sleep_for


class AntiCrawlStrategy:
    """反爬策略聚合：代理 + UA + 频率控制 + Playwright 模拟真人接口"""

    def __init__(
        self,
        proxies: Optional[List[str]] = None,
        min_interval_s: float = 2.0,
        max_interval_s: float = 5.0,
    ):
        self.proxy_pool = ProxyPool(proxies)
        self.ua_rotator = UserAgentRotator()
        self.rate_limiter = RateLimiter(min_interval_s, max_interval_s)
        log.info("AntiCrawlStrategy 初始化完成")

    def build_headers(self) -> Dict[str, str]:
        """生成请求头（包含轮换后的 UA）"""
        return {
            "User-Agent": self.ua_rotator.next(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    def request(self, url: str) -> Dict[str, Any]:
        """执行一个普通 HTTP 请求，自动控制频率并附加 UA/代理"""
        self.rate_limiter.wait()
        headers = self.build_headers()
        proxy = self.proxy_pool.next()
        try:
            import httpx  # 延迟导入
            with httpx.Client(proxy=proxy, timeout=10.0, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                return {"status": resp.status_code, "text": resp.text[:2000], "proxy": proxy}
        except Exception as e:  # noqa: BLE001
            log.warning(f"反爬请求失败 url={url} proxy={proxy} err={e}")
            return {"status": -1, "text": "", "error": str(e)}

    # ---- Playwright 模拟真人 ----
    def human_like_browse(self, url: str, scroll: bool = True, wait_ms: int = 1500) -> Dict[str, Any]:
        """使用 Playwright 模拟真人访问（提供接口骨架，未安装时返回提示）"""
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except ImportError:
            log.warning("Playwright 未安装，请先 `pip install playwright && playwright install`")
            return {"status": -1, "text": "", "error": "playwright not installed"}

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                ctx = browser.new_context(
                    user_agent=self.ua_rotator.next(),
                    viewport={"width": 1366, "height": 768},
                    locale="zh-CN",
                )
                page = ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(wait_ms)
                if scroll:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                    page.wait_for_timeout(500)
                text = page.inner_text("body")[:3000]
                browser.close()
                return {"status": 200, "text": text, "mode": "playwright"}
        except Exception as e:  # noqa: BLE001
            log.error(f"Playwright 模拟访问失败: {e}")
            return {"status": -1, "text": "", "error": str(e)}


# ===========================================================
# 2. 大模型稳定性保障
# ===========================================================
@dataclass
class LLMCallResult:
    success: bool
    data: Any = None
    raw: str = ""
    error: str = ""
    attempt: int = 0
    elapsed_ms: float = 0.0


class LLMStabilityGuard:
    """大模型稳定性保障

    - JSON Schema 强制校验
    - 输出后正则校验
    - 自动重试（指数退避）
    - 失败降级到 mock 模式
    """

    def __init__(self, max_retries: int = 3, backoff_base: float = 1.5, enable_mock_fallback: bool = True):
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.enable_mock_fallback = enable_mock_fallback

    # ---- Schema 校验 ----
    def validate_schema(self, data: Any, schema: Dict[str, Any]) -> Tuple[bool, str]:
        """极简 JSON Schema 校验：仅支持 type / required / properties"""
        try:
            if not isinstance(data, dict):
                return False, "root is not object"

            for key in schema.get("required", []):
                if key not in data:
                    return False, f"missing field: {key}"

            props: Dict[str, Any] = schema.get("properties", {})
            for k, sub in props.items():
                if k not in data:
                    continue
                expected = sub.get("type")
                val = data[k]
                if expected == "string" and not isinstance(val, str):
                    return False, f"field {k} expected string"
                if expected == "integer" and not isinstance(val, int):
                    return False, f"field {k} expected integer"
                if expected == "number" and not isinstance(val, (int, float)):
                    return False, f"field {k} expected number"
                if expected == "array" and not isinstance(val, list):
                    return False, f"field {k} expected array"
                if expected == "object" and not isinstance(val, dict):
                    return False, f"field {k} expected object"
            return True, ""
        except Exception as e:  # noqa: BLE001
            return False, f"schema_validate_error: {e}"

    # ---- 正则校验 ----
    def validate_regex(self, text: str, patterns: List[str]) -> Tuple[bool, str]:
        for p in patterns:
            if not re.search(p, text):
                return False, f"regex_not_match: {p}"
        return True, ""

    # ---- 解析 JSON ----
    @staticmethod
    def safe_json_parse(raw: str) -> Tuple[bool, Any, str]:
        try:
            # 容忍 ```json ... ``` 包装
            m = re.search(r"\{[\s\S]*\}", raw)
            payload = m.group(0) if m else raw
            return True, json.loads(payload), ""
        except Exception as e:  # noqa: BLE001
            return False, None, f"json_parse_error: {e}"

    def call(
        self,
        caller: Callable[[], str],
        schema: Optional[Dict[str, Any]] = None,
        regex_patterns: Optional[List[str]] = None,
        mock_fn: Optional[Callable[[], Any]] = None,
    ) -> LLMCallResult:
        """主入口：调用大模型 + 校验 + 重试 + 降级"""
        start = time.time()
        last_error = ""
        raw = ""

        for attempt in range(1, self.max_retries + 1):
            try:
                raw = caller() or ""
                ok_json, data, err = self.safe_json_parse(raw)
                if not ok_json:
                    last_error = err
                    raise ValueError(err)

                if schema:
                    ok, err = self.validate_schema(data, schema)
                    if not ok:
                        last_error = err
                        raise ValueError(err)

                if regex_patterns:
                    ok, err = self.validate_regex(raw, regex_patterns)
                    if not ok:
                        last_error = err
                        raise ValueError(err)

                return LLMCallResult(
                    success=True,
                    data=data,
                    raw=raw,
                    attempt=attempt,
                    elapsed_ms=(time.time() - start) * 1000,
                )
            except Exception as e:  # noqa: BLE001
                last_error = f"{type(e).__name__}: {e}"
                log.warning(f"LLM 调用第 {attempt} 次失败: {last_error}")
                if attempt < self.max_retries:
                    time.sleep(self.backoff_base ** attempt)

        # 降级到 mock
        if self.enable_mock_fallback:
            try:
                mock_data = mock_fn() if mock_fn else self._default_mock(raw)
                log.warning(f"LLM 降级到 mock 模式，原因: {last_error}")
                return LLMCallResult(
                    success=True,
                    data=mock_data,
                    raw=raw,
                    attempt=self.max_retries,
                    error=last_error,
                    elapsed_ms=(time.time() - start) * 1000,
                )
            except Exception as e:  # noqa: BLE001
                last_error = f"{last_error} | mock_error: {e}"

        return LLMCallResult(
            success=False,
            raw=raw,
            error=last_error,
            attempt=self.max_retries,
            elapsed_ms=(time.time() - start) * 1000,
        )

    @staticmethod
    def _default_mock(raw: str) -> Dict[str, Any]:
        """当未提供 mock_fn 时返回一个安全的默认结构"""
        return {
            "mock": True,
            "raw_excerpt": (raw or "")[:200],
            "skills": [],
            "note": "LLM call failed, fallback to mock",
        }


# ===========================================================
# 3. Neo4j 性能优化
# ===========================================================
class LRUCache:
    """线程安全的 LRU 缓存（基于 OrderedDict）"""

    def __init__(self, capacity: int = 1024):
        self.capacity = capacity
        self._data: "OrderedDict[str, Any]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            if key not in self._data:
                return None
            self._data.move_to_end(key)
            return self._data[key]

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = value
            while len(self._data) > self.capacity:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {"size": len(self._data), "capacity": self.capacity}


class Neo4jPerformanceOptimizer:
    """Neo4j 性能优化器

    - 按领域分库策略（接口）
    - 查询缓存（LRU，可替换为 Redis）
    - 批量写入优化（UNWIND + 参数化）
    - 慢查询日志
    """

    SLOW_QUERY_THRESHOLD_MS = 200.0

    def __init__(self, cache_capacity: int = 1024, redis_client: Any = None):
        self.cache = LRUCache(capacity=cache_capacity)
        self._redis = redis_client  # 可选：注入 redis 客户端
        self._slow_logs: List[Dict[str, Any]] = []

    # ---- 分库策略 ----
    @staticmethod
    def shard_db_name(domain: str) -> str:
        """根据领域返回目标数据库名（生产环境可改为路由到不同集群）"""
        domain = (domain or "default").lower()
        mapping = {
            "互联网": "neo4j_internet",
            "金融": "neo4j_finance",
            "制造": "neo4j_manufacturing",
            "医疗": "neo4j_healthcare",
        }
        for k, v in mapping.items():
            if k in domain:
                return v
        return "neo4j_default"

    def get_session_for_domain(self, domain: str) -> Any:
        """获取指定域的 session（接口骨架）"""
        from app.core.neo4j_db import neo4j_client
        if neo4j_client._driver is None:
            return None
        return neo4j_client.get_session(database=self.shard_db_name(domain))

    # ---- 查询缓存 ----
    def _cache_key(self, cypher: str, params: Dict[str, Any]) -> str:
        h = hashlib.sha1()
        h.update(cypher.encode("utf-8"))
        h.update(json.dumps(params, sort_keys=True, default=str).encode("utf-8"))
        return h.hexdigest()

    def cached_query(self, session: Any, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """带缓存的查询：先 LRU -> Redis -> 真正执行"""
        params = params or {}
        key = self._cache_key(cypher, params)

        cached = self.cache.get(key)
        if cached is not None:
            return cached

        if self._redis is not None:
            try:
                import pickle
                raw = self._redis.get(key)
                if raw:
                    data = pickle.loads(raw)
                    self.cache.put(key, data)
                    return data
            except Exception:  # noqa: BLE001
                pass

        if session is None:
            return []

        start = time.time()
        try:
            result = session.run(cypher, params)
            data = [dict(r) for r in result]
        except Exception as e:  # noqa: BLE001
            log.error(f"Cypher 执行失败: {e}")
            return []

        elapsed_ms = (time.time() - start) * 1000
        if elapsed_ms >= self.SLOW_QUERY_THRESHOLD_MS:
            self._slow_logs.append({
                "cypher": cypher[:200],
                "params": {k: str(v)[:80] for k, v in params.items()},
                "elapsed_ms": round(elapsed_ms, 2),
                "ts": datetime.now().isoformat(timespec="seconds"),
            })
            log.warning(f"慢查询 {elapsed_ms:.1f}ms: {cypher[:80]}")

        self.cache.put(key, data)
        if self._redis is not None:
            try:
                import pickle
                self._redis.setex(key, 300, pickle.dumps(data))  # 5 分钟
            except Exception:  # noqa: BLE001
                pass
        return data

    # ---- 批量写入（UNWIND） ----
    def batch_upsert(self, session: Any, label: str, rows: List[Dict[str, Any]], unique_key: str) -> int:
        """使用 UNWIND 批量 upsert 节点"""
        if not rows or session is None:
            return 0
        cypher = (
            f"UNWIND $rows AS row "
            f"MERGE (n:{label} {{ {unique_key}: row.`{unique_key}` }}) "
            f"SET n += row"
        )
        try:
            session.run(cypher, rows=rows)
            return len(rows)
        except Exception as e:  # noqa: BLE001
            log.error(f"批量写入 {label} 失败: {e}")
            return 0

    def batch_create_relations(
        self,
        session: Any,
        rel_type: str,
        from_label: str,
        from_key: str,
        to_label: str,
        to_key: str,
        rows: List[Dict[str, Any]],
    ) -> int:
        """批量创建关系"""
        if not rows or session is None:
            return 0
        cypher = (
            f"UNWIND $rows AS row "
            f"MATCH (a:{from_label} {{ {from_key}: row.from_val }}), "
            f"      (b:{to_label} {{ {to_key}: row.to_val }}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            f"SET r += row.props"
        )
        params = {
            "rows": [
                {
                    "from_val": r["from"],
                    "to_val": r["to"],
                    "props": r.get("props", {}),
                }
                for r in rows
            ]
        }
        try:
            session.run(cypher, params=params)
            return len(rows)
        except Exception as e:  # noqa: BLE001
            log.error(f"批量创建关系 {rel_type} 失败: {e}")
            return 0

    def slow_query_logs(self) -> List[Dict[str, Any]]:
        return list(self._slow_logs)

    def clear_slow_logs(self) -> None:
        self._slow_logs.clear()


# ===========================================================
# 4. 优先级调度
# ===========================================================
@dataclass
class ScheduledTask:
    name: str
    fn: Callable[[], Any]
    priority: int  # 数字越小，优先级越高
    created_at: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)

    def run(self) -> Dict[str, Any]:
        start = time.time()
        try:
            res = self.fn()
            return {
                "name": self.name,
                "success": True,
                "duration_ms": round((time.time() - start) * 1000, 2),
                "result": res,
            }
        except Exception as e:  # noqa: BLE001
            return {
                "name": self.name,
                "success": False,
                "duration_ms": round((time.time() - start) * 1000, 2),
                "error": f"{type(e).__name__}: {e}",
            }


# 任务优先级常量
PRIORITY_NEW_ROLE_DISCOVERY = 10   # 新岗位发现（最高）
PRIORITY_GRAPH_UPDATE = 20         # 图谱更新
PRIORITY_MATCHING = 30             # 匹配
PRIORITY_RESUME_PARSE = 40         # 简历解析
PRIORITY_BATCH_CLEAN = 50          # 批处理清洗（最低）


class PriorityScheduler:
    """基础优先级调度器：按优先级顺序消费任务队列"""

    def __init__(self):
        self._queue: List[ScheduledTask] = []
        self._lock = threading.Lock()

    def submit(self, task: ScheduledTask) -> None:
        with self._lock:
            self._queue.append(task)
            self._queue.sort(key=lambda t: (t.priority, t.created_at))

    def add(self, name: str, fn: Callable[[], Any], priority: int = 40, payload: Optional[Dict[str, Any]] = None) -> None:
        self.submit(ScheduledTask(name=name, fn=fn, priority=priority, payload=payload or {}))

    def drain(self, max_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """按优先级取出并执行任务，返回每条任务结果"""
        results: List[Dict[str, Any]] = []
        with self._lock:
            tasks = self._queue[: max_n] if max_n else list(self._queue)
            del self._queue[: max_n] if max_n else self._queue[:]
        for t in tasks:
            results.append(t.run())
        return results

    def size(self) -> int:
        with self._lock:
            return len(self._queue)


# ===========================================================
# 顶层 RiskHandler 聚合
# ===========================================================
class RiskHandler:
    """风险与性能策略聚合入口"""

    def __init__(self, redis_client: Any = None):
        self.anti_crawl = AntiCrawlStrategy()
        self.llm_guard = LLMStabilityGuard()
        self.neo4j_opt = Neo4jPerformanceOptimizer(redis_client=redis_client)
        self.scheduler = PriorityScheduler()
        log.info("RiskHandler 初始化完成")


# ===========================================================
# 装饰器：用于把 LLM 调用接入稳定性保障
# ===========================================================
def guarded_llm(schema: Optional[Dict[str, Any]] = None, regex_patterns: Optional[List[str]] = None):
    """装饰器：把一个返回 raw 字符串的 LLM 函数接入 LLMStabilityGuard"""
    def deco(fn: Callable[..., str]) -> Callable[..., LLMCallResult]:
        @wraps(fn)
        def wrapper(*args, **kwargs) -> LLMCallResult:
            guard = LLMStabilityGuard()
            return guard.call(
                caller=lambda: fn(*args, **kwargs),
                schema=schema,
                regex_patterns=regex_patterns,
            )
        return wrapper
    return deco
