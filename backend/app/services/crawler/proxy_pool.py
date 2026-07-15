"""代理池

提供：
* :class:`ProxyPool`    - 简单环形代理池
* :func:`get_default_proxy_pool` - 获取带示例代理的默认池

示例代理仅用于演示，生产环境应通过代理供应商 API 注入。
"""
from __future__ import annotations

import random
import threading
import time
from collections import deque
from typing import List, Optional

from app.core.logger import log


# 默认示例代理（占位 IP；离线环境会立即失败，由 :meth:`mark_failed` 自动切换）
_DEFAULT_SAMPLE_PROXIES: List[str] = [
    "http://127.0.0.1:8888",
    "http://127.0.0.1:8889",
    "http://127.0.0.1:8890",
]


class ProxyPool:
    """轻量级代理池

    Features:
        * 环形选择
        * 失败标记（自动降级跳过坏代理）
        * 健康检查（启动时可选）
        * 线程安全
    """

    def __init__(
        self,
        proxies: Optional[List[str]] = None,
        health_check: bool = False,
        max_failures: int = 3,
    ) -> None:
        self._pool: deque = deque(proxies or _DEFAULT_SAMPLE_PROXIES)
        self._failures: dict = {}
        self.max_failures = int(max_failures)
        self._lock = threading.Lock()
        if health_check:
            self.health_check_all()

    # -------------------------------------------------------- 公共接口
    def get(self) -> Optional[str]:
        """获取一个可用代理（轮询）"""
        with self._lock:
            for _ in range(len(self._pool)):
                if not self._pool:
                    return None
                proxy = self._pool[0]
                self._pool.rotate(-1)
                if self._failures.get(proxy, 0) < self.max_failures:
                    return proxy
            return None

    def rotate(self) -> Optional[str]:
        """强制轮换：跳过当前头部返回下一个"""
        with self._lock:
            if not self._pool:
                return None
            self._pool.rotate(-1)
            return self._pool[0]

    def mark_failed(self, proxy: str) -> None:
        """标记代理失败，超阈值后从池中移除"""
        with self._lock:
            self._failures[proxy] = self._failures.get(proxy, 0) + 1
            if self._failures[proxy] >= self.max_failures:
                try:
                    self._pool.remove(proxy)
                    log.warning(f"代理 {proxy} 已达到失败阈值，移除出池")
                except ValueError:
                    pass

    def mark_success(self, proxy: str) -> None:
        """标记代理成功（清零失败计数）"""
        with self._lock:
            self._failures[proxy] = 0

    def add(self, proxy: str) -> None:
        """动态加入新代理"""
        if not proxy:
            return
        with self._lock:
            if proxy not in self._pool:
                self._pool.append(proxy)
                log.info(f"代理 {proxy} 已加入池")

    def all(self) -> List[str]:
        """返回当前池中所有代理"""
        with self._lock:
            return list(self._pool)

    def size(self) -> int:
        with self._lock:
            return len(self._pool)

    def health_check_all(self, timeout: float = 2.0) -> None:
        """同步健康检查（通过 https://httpbin.org/ip）。
        生产可换成自建探测服务；示例为可选，默认关闭。
        """
        try:
            import httpx
        except Exception:  # noqa: BLE001
            log.debug("httpx 未安装，跳过健康检查")
            return
        for proxy in list(self._pool):
            try:
                with httpx.Client(proxy=proxy, timeout=timeout) as client:
                    r = client.get("https://httpbin.org/ip")
                    if r.status_code == 200:
                        self.mark_success(proxy)
                    else:
                        self.mark_failed(proxy)
            except Exception:  # noqa: BLE001
                self.mark_failed(proxy)
        log.info(f"代理池健康检查完成，可用代理: {self.size()}")


_default_pool: Optional[ProxyPool] = None
_default_lock = threading.Lock()


def get_default_proxy_pool() -> ProxyPool:
    """获取/创建进程级默认代理池单例"""
    global _default_pool
    with _default_lock:
        if _default_pool is None:
            _default_pool = ProxyPool(proxies=_DEFAULT_SAMPLE_PROXIES, health_check=False)
        return _default_pool


__all__ = ["ProxyPool", "get_default_proxy_pool"]
