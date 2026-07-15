"""爬虫抽象基类与公共数据结构

定义：
* :class:`JDItem` - 单条 JD 数据结构
* :class:`BaseCrawler` - 所有 Spider 的抽象基类
* :data:`DEFAULT_USER_AGENTS` - 默认 UA 池
"""
from __future__ import annotations

import asyncio
import random
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.logger import log


# ============================================================
# 默认 UA 池
# ============================================================
DEFAULT_USER_AGENTS: List[str] = [
    # Chrome / Win
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Chrome / Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox / Win
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) "
    "Gecko/20100101 Firefox/124.0",
    # Safari / Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Linux Chrome
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]


# ============================================================
# JDItem
# ============================================================
@dataclass
class JDItem:
    """单条 JD 数据结构

    Attributes:
        jd_id: 全局唯一 ID（爬虫内部生成，跨源去重依赖此字段）
        source: 数据来源标识（如 boss / zhilian / liepin / onet 等）
        source_url: 原始 URL
        company: 公司名
        title: 岗位名称
        category: 岗位类别（粗分类）
        level: 级别（初级 / 中级 / 高级 / 资深）
        location: 工作地点
        salary_range: 薪资范围（统一格式如 ``20K-30K``）
        raw_text: 原始 JD 文本（未清洗）
        skills: 初始技能列表（爬虫层尽量抽取简单关键字）
        published_at: JD 发布时间（ISO 字符串）
        extra: 其它元数据（如 JSON-LD 字段）
    """

    jd_id: str
    source: str
    source_url: str = ""
    company: str = ""
    title: str = ""
    category: str = ""
    level: str = ""
    location: str = ""
    salary_range: str = ""
    raw_text: str = ""
    skills: List[str] = field(default_factory=list)
    published_at: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 序列化）"""
        return asdict(self)


# ============================================================
# BaseCrawler
# ============================================================
class BaseCrawler(ABC):
    """所有 Spider 的抽象基类

    统一接口：
        * :meth:`fetch`  - 拉取一个 URL，返回 HTML 文本
        * :meth:`parse`  - 解析 HTML 文本，返回中间结构（子类可重写）
        * :meth:`save`   - 持久化（默认写到内存列表，子类可改为写 ES / MySQL / 文件）
        * :meth:`crawl`  - 主流程：循环 fetch + parse + save

    反爬设计（默认开启）：
        * UA 轮换
        * 随机延时（min_interval ~ max_interval 之间）
        * 失败指数退避重试
        * 可选代理（通过 :class:`ProxyPool` 注入）
    """

    # 子类需覆盖
    source_name: str = "base"
    base_url: str = ""

    def __init__(
        self,
        use_mock: bool = True,
        min_interval: float = 1.0,
        max_interval: float = 3.0,
        max_retries: int = 3,
        timeout: float = 15.0,
        proxies: Optional["ProxyPool"] = None,  # type: ignore[name-defined]
    ) -> None:
        self.use_mock = use_mock
        self.min_interval = float(min_interval)
        self.max_interval = float(max_interval)
        self.max_retries = int(max_retries)
        self.timeout = float(timeout)
        # 代理池：延迟导入避免循环
        if proxies is None:
            from app.services.crawler.proxy_pool import get_default_proxy_pool
            proxies = get_default_proxy_pool()
        self.proxies = proxies
        # 请求计数
        self._req_count = 0
        self._last_request_ts = 0.0
        self._lock = asyncio.Lock()

    # -------------------------------------------------------- 抽象接口
    @abstractmethod
    async def fetch(self, url: str) -> Optional[str]:
        """拉取一个 URL，返回 HTML 文本；失败返回 None"""
        raise NotImplementedError

    @abstractmethod
    def parse(self, html: str, **kwargs) -> List[JDItem]:
        """从 HTML 抽取 JDItem 列表"""
        raise NotImplementedError

    def save(self, items: List[JDItem]) -> List[JDItem]:
        """持久化（默认原样返回，子类可改为写库/写文件）"""
        return items

    # -------------------------------------------------------- 公共工具
    def make_jd_id(self, prefix: str, idx: int) -> str:
        """生成 JD ID：``{prefix}-{ts}-{idx:05d}``"""
        return f"{prefix}-{int(time.time())}-{idx:05d}"

    def pick_ua(self) -> str:
        """UA 轮换"""
        return random.choice(DEFAULT_USER_AGENTS)

    async def throttle(self) -> None:
        """频率控制：两次请求间隔至少 min_interval 秒"""
        async with self._lock:
            now = time.time()
            target = random.uniform(self.min_interval, self.max_interval)
            wait = target - (now - self._last_request_ts)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_ts = time.time()
            self._req_count += 1

    @staticmethod
    def salary_normalize(text: str) -> str:
        """把形如 ``20-30K·14薪`` 统一为 ``20K-30K``"""
        if not text:
            return ""
        m = re.search(r"(\d+)\s*[-~—到至]\s*(\d+)\s*([Kk万])", text)
        if m:
            return f"{m.group(1)}K-{m.group(2)}K"
        m = re.search(r"(\d+)\s*([Kk万])", text)
        if m:
            return f"{m.group(1)}K"
        return text.strip()

    @staticmethod
    def parse_html(html: str, selector: Optional[str] = None) -> List[BeautifulSoup]:
        """解析 HTML，返回匹配节点列表（无 selector 时返回整页）"""
        soup = BeautifulSoup(html or "", "lxml")
        if not selector:
            return [soup]
        try:
            return soup.select(selector)
        except Exception as e:  # noqa: BLE001
            log.error(f"CSS 选择器解析失败 {selector}: {e}")
            return [soup]

    async def request_with_retry(self, url: str) -> Optional[str]:
        """带反爬/重试的通用 GET 请求，子类 fetch() 可直接调用"""
        import httpx
        last_err: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                await self.throttle()
                proxy = self.proxies.get() if self.proxies else None
                headers = {
                    "User-Agent": self.pick_ua(),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                }
                async with httpx.AsyncClient(
                    timeout=self.timeout, follow_redirects=True, proxy=proxy
                ) as client:
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    return resp.text
            except Exception as e:  # noqa: BLE001
                last_err = e
                log.warning(
                    f"[{self.source_name}] GET 失败 {url} (尝试 {attempt}/{self.max_retries}): {e}"
                )
                await asyncio.sleep(2 ** attempt * 0.5)
        log.error(f"[{self.source_name}] GET 最终失败 {url}: {last_err}")
        return None

    # -------------------------------------------------------- 主流程
    async def crawl(self, keyword: str = "", pages: int = 1) -> List[JDItem]:
        """主流程：默认调用 mock；子类可覆盖以实现真实抓取"""
        if self.use_mock:
            return self._crawl_mock(keyword, pages)
        # 在线模式由各 Spider 实现
        log.warning(f"[{self.source_name}] 未实现在线模式，回退到 mock")
        return self._crawl_mock(keyword, pages)

    def _crawl_mock(self, keyword: str, pages: int) -> List[JDItem]:
        """默认 mock 路径：从 :mod:`mock_data` 生成"""
        from app.services.mock_data import MockJDGenerator
        gen = MockJDGenerator()
        count = min(max(pages * 10, 5), 50)
        items = gen.generate(count, category_filter=keyword or None, source=self.source_name)
        return self.save(items)


__all__ = ["JDItem", "BaseCrawler", "DEFAULT_USER_AGENTS"]
