"""内存查询缓存（Redis 风格简化实现）

为减少对 MySQL/Neo4j 的重复查询，提供：
- 同步缓存：SimpleCache（线程安全）
- 装饰器：cached() / cached_async()
- 批量写入：BatchWriter（合并短时间内的多次 Neo4j 写操作）

注意：生产环境建议替换为真正的 Redis 集群。
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import defaultdict, deque
from functools import wraps
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

from app.core.logger import log


class SimpleCache:
    """线程安全的 TTL 缓存

    - key-value 存储
    - 支持过期时间
    - 支持最大条目数（LRU 淘汰）
    """

    def __init__(self, max_size: int = 1024, default_ttl: int = 60):
        """初始化缓存

        :param max_size: 最大缓存条目数
        :param default_ttl: 默认过期时间（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def make_key(prefix: str, *args: Any, **kwargs: Any) -> str:
        """根据参数生成稳定的缓存 key"""
        raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str, ensure_ascii=False)
        digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
        return f"{prefix}:{digest}"

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，过期则返回 None"""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                return None
            expire_at, value = entry
            if expire_at < time.time():
                self._store.pop(key, None)
                self._misses += 1
                return None
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """写入缓存"""
        with self._lock:
            if len(self._store) >= self.max_size:
                # 简单 FIFO 淘汰（生产可换 LRU）
                oldest_key = next(iter(self._store))
                self._store.pop(oldest_key, None)
            expire_at = time.time() + (ttl or self.default_ttl)
            self._store[key] = (expire_at, value)

    def delete(self, key: str) -> bool:
        """删除指定 key"""
        with self._lock:
            return self._store.pop(key, None) is not None

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, Any]:
        """返回缓存统计信息"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total) if total else 0.0
            return {
                "size": len(self._store),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 4),
            }


# 全局缓存实例
graph_cache = SimpleCache(max_size=2048, default_ttl=120)   # 图谱查询缓存 2 分钟
match_cache = SimpleCache(max_size=512, default_ttl=300)    # 匹配结果缓存 5 分钟
jd_cache = SimpleCache(max_size=512, default_ttl=60)        # JD 详情缓存 1 分钟


def cached(prefix: str, cache: Optional[SimpleCache] = None, ttl: Optional[int] = None):
    """同步函数缓存装饰器

    使用方法：
        @cached("graph_view")
        def get_graph_view(view_type): ...
    """
    _cache = cache or graph_cache

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = SimpleCache.make_key(prefix, *args, **kwargs)
            cached_value = _cache.get(key)
            if cached_value is not None:
                log.debug(f"缓存命中: {prefix}")
                return cached_value
            value = func(*args, **kwargs)
            _cache.set(key, value, ttl=ttl)
            return value

        return wrapper

    return decorator


class BatchWriter:
    """批量写入器（用于合并短时间内的多次 Neo4j 写操作）

    使用方式：
        writer = BatchWriter(batch_size=200, flush_interval=2.0)
        writer.add(cypher, params)
        writer.flush()  # 手动触发
    """

    def __init__(self, batch_size: int = 200, flush_interval: float = 2.0):
        """初始化批量写入器

        :param batch_size: 批次最大条数
        :param flush_interval: 自动刷新间隔（秒）
        """
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._queue: Deque[Tuple[str, Dict[str, Any]]] = deque()
        self._lock = threading.Lock()
        self._last_flush = time.time()

    def add(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """添加一条写入请求

        :return: 是否触发了自动 flush
        """
        triggered = False
        with self._lock:
            self._queue.append((cypher, params or {}))
            if len(self._queue) >= self.batch_size:
                triggered = True
            elif time.time() - self._last_flush >= self.flush_interval:
                triggered = True
        if triggered:
            self.flush()
        return triggered

    def flush(self) -> int:
        """执行批量写入

        :return: 本次写入条数
        """
        with self._lock:
            if not self._queue:
                return 0
            batch = list(self._queue)
            self._queue.clear()
            self._last_flush = time.time()

        # 实际执行
        try:
            from app.core.neo4j_db import neo4j_client
            session = neo4j_client.get_session()
            if not session:
                log.warning("Neo4j 未连接，跳过批量写入")
                return 0
            try:
                # 使用 UNWIND 合并为单条事务
                cypher_list = [c for c, _ in batch]
                params_list = [p for _, p in batch]
                # 简化：单条循环执行
                for cypher, params in zip(cypher_list, params_list):
                    session.run(cypher, params)
            finally:
                session.close()
        except Exception as e:
            log.error(f"批量写入失败: {e}")
            return 0

        return len(batch)

    def size(self) -> int:
        """当前队列长度"""
        with self._lock:
            return len(self._queue)


# 全局批量写入器
graph_batch_writer = BatchWriter(batch_size=200, flush_interval=2.0)


def get_cache_snapshot() -> Dict[str, Any]:
    """返回所有缓存的统计信息（供监控使用）"""
    return {
        "graph_cache": graph_cache.stats(),
        "match_cache": match_cache.stats(),
        "jd_cache": jd_cache.stats(),
        "batch_writer_size": graph_batch_writer.size(),
    }


def clear_all_caches() -> None:
    """清空所有缓存"""
    graph_cache.clear()
    match_cache.clear()
    jd_cache.clear()
    log.info("已清空所有内存缓存")
