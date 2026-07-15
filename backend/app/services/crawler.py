"""多源异构数据采集模块

提供：
1. BaseCrawler 抽象基类：定义统一爬虫接口
2. HTTPClient 通用 HTTP 客户端：UA 轮换、限速、重试
3. ProxyPool 代理池：从文件加载代理列表
4. 多个平台 Spider 模板（BOSS直聘 / 智联 / 猎聘 / 企业官网 / 行业报告 / 政策文件 / O*NET）
5. MockJDGenerator：从 mock_data 模块重导出，便于统一调用

由于环境无法访问外网，Spider 模板默认走"模板渲染 + 模拟数据回退"路径，
真实部署时只需替换 fetch() 即可。
"""
from __future__ import annotations

import asyncio
import os
import random
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.logger import log


# ============================================================
# 数据结构
# ============================================================
@dataclass
class JDItem:
    """单条 JD 数据结构。"""
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
        return {
            "jd_id": self.jd_id,
            "source": self.source,
            "source_url": self.source_url,
            "company": self.company,
            "title": self.title,
            "category": self.category,
            "level": self.level,
            "location": self.location,
            "salary_range": self.salary_range,
            "raw_text": self.raw_text,
            "skills": self.skills,
            "published_at": self.published_at,
            "extra": self.extra,
        }


# ============================================================
# 通用 HTTP 客户端
# ============================================================
DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


class ProxyPool:
    """代理池：从文本文件按行读取代理（http://ip:port 或 ip:port）。"""

    def __init__(self, proxy_file: str = "./data/proxies.txt"):
        self.proxy_file = proxy_file
        self._proxies: List[str] = []
        self._idx = 0
        self.reload()

    def reload(self) -> None:
        """从文件重新加载代理。"""
        if not os.path.exists(self.proxy_file):
            log.debug(f"代理文件不存在 {self.proxy_file}，使用空代理池")
            self._proxies = []
            return
        try:
            with open(self.proxy_file, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
            self._proxies = [
                ln if ln.startswith("http") else f"http://{ln}" for ln in lines
            ]
            log.info(f"代理池加载完成：{len(self._proxies)} 条")
        except Exception as e:
            log.error(f"代理池加载失败: {e}")
            self._proxies = []

    def get(self) -> Optional[str]:
        if not self._proxies:
            return None
        proxy = self._proxies[self._idx % len(self._proxies)]
        self._idx += 1
        return proxy


class HTTPClient:
    """通用异步 HTTP 客户端：UA 轮换 + 限速 + 失败重试 + 代理。"""

    def __init__(
        self,
        proxies: Optional[ProxyPool] = None,
        min_interval: float = 1.0,
        max_interval: float = 3.0,
        max_retries: int = 3,
        timeout: float = 15.0,
    ):
        self.proxies = proxies or ProxyPool()
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.max_retries = max_retries
        self.timeout = timeout
        self._last_request_ts = 0.0
        self._lock = asyncio.Lock()

    def _pick_ua(self) -> str:
        return random.choice(DEFAULT_USER_AGENTS)

    def _pick_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self._pick_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    async def _throttle(self) -> None:
        async with self._lock:
            now = time.time()
            wait = self.max_interval - (now - self._last_request_ts)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_ts = time.time()

    async def get(self, url: str, **kwargs) -> Optional[str]:
        """带重试的 GET 请求，返回 HTML 文本。"""
        last_err: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                await self._throttle()
                proxy = self.proxies.get()
                async with httpx.AsyncClient(
                    timeout=self.timeout, follow_redirects=True, proxy=proxy
                ) as client:
                    resp = await client.get(url, headers=self._pick_headers(), **kwargs)
                    resp.raise_for_status()
                    return resp.text
            except Exception as e:  # noqa: BLE001
                last_err = e
                log.warning(f"HTTP GET 失败 {url}（尝试 {attempt}/{self.max_retries}）: {e}")
                await asyncio.sleep(2 ** attempt * 0.5)
        log.error(f"HTTP GET 最终失败 {url}: {last_err}")
        return None

    @staticmethod
    def parse_html(html: str, selector: Optional[str] = None) -> List[BeautifulSoup]:
        """解析 HTML，返回匹配节点列表（无 selector 时返回整页）。"""
        soup = BeautifulSoup(html or "", "lxml")
        if not selector:
            return [soup]
        try:
            return soup.select(selector)
        except Exception as e:  # noqa: BLE001
            log.error(f"CSS 选择器解析失败 {selector}: {e}")
            return [soup]


# ============================================================
# 抽象基类
# ============================================================
class BaseCrawler(ABC):
    """所有 Spider 的抽象基类。"""

    source_name: str = "base"
    base_url: str = ""

    def __init__(self, http: Optional[HTTPClient] = None, use_mock: bool = True):
        self.http = http or HTTPClient()
        self.use_mock = use_mock  # 离线环境直接走模拟数据

    @abstractmethod
    async def crawl(self, keyword: str = "", pages: int = 1) -> List[JDItem]:
        """统一爬取接口：按关键词、页数返回 JDItem 列表。"""
        raise NotImplementedError

    # ------- 公共工具方法 -------
    def make_jd_id(self, prefix: str, idx: int) -> str:
        return f"{prefix}-{int(time.time())}-{idx:05d}"

    def salary_normalize(self, text: str) -> str:
        """把形如 '20-30K·14薪' 统一为 '20K-30K'。"""
        if not text:
            return ""
        m = re.search(r"(\d+)\s*[-~—]\s*(\d+)\s*([Kk万])", text)
        if m:
            return f"{m.group(1)}K-{m.group(2)}K"
        m = re.search(r"(\d+)\s*([Kk万])", text)
        if m:
            return f"{m.group(1)}K"
        return text.strip()

    async def fetch(self, url: str) -> Optional[str]:
        return await self.http.get(url)

    def parse(self, html: str) -> List[BeautifulSoup]:
        return HTTPClient.parse_html(html)


# ============================================================
# BOSS 直聘
# ============================================================
class BossSpider(BaseCrawler):
    """BOSS直聘 JD 采集（模板实现：默认走模拟数据回退）。"""

    source_name = "boss"
    base_url = "https://www.zhipin.com"

    async def crawl(self, keyword: str = "Python", pages: int = 1) -> List[JDItem]:
        log.info(f"[BossSpider] keyword={keyword} pages={pages}")
        # 离线环境直接走模拟生成
        if self.use_mock:
            from app.services.mock_data import MockJDGenerator
            gen = MockJDGenerator()
            items = gen.generate(min(pages * 10, 30), category_filter=keyword or None, source="boss")
            for it in items:
                it.source_url = it.source_url or f"{self.base_url}/job/{it.jd_id}.html"
            return items
        # 在线模板
        results: List[JDItem] = []
        for page in range(1, pages + 1):
            url = f"{self.base_url}/web/geek/job?query={keyword}&page={page}"
            html = await self.fetch(url)
            if not html:
                continue
            nodes = self.parse(html)
            for i, node in enumerate(nodes):
                try:
                    title = node.select_one(".job-name").get_text(strip=True) if node.select_one(".job-name") else ""
                    company = node.select_one(".company-name").get_text(strip=True) if node.select_one(".company-name") else ""
                    salary = node.select_one(".salary").get_text(strip=True) if node.select_one(".salary") else ""
                    results.append(JDItem(
                        jd_id=self.make_jd_id("boss", page * 100 + i),
                        source=self.source_name,
                        source_url=url,
                        company=company,
                        title=title,
                        salary_range=self.salary_normalize(salary),
                        raw_text=str(node)[:2000],
                    ))
                except Exception as e:  # noqa: BLE001
                    log.error(f"[BossSpider] 解析失败: {e}")
        return results


# ============================================================
# 智联招聘
# ============================================================
class ZhilianSpider(BaseCrawler):
    """智联招聘 JD 采集。"""

    source_name = "zhilian"
    base_url = "https://www.zhaopin.com"

    async def crawl(self, keyword: str = "Python", pages: int = 1) -> List[JDItem]:
        log.info(f"[ZhilianSpider] keyword={keyword} pages={pages}")
        if self.use_mock:
            from app.services.mock_data import MockJDGenerator
            gen = MockJDGenerator()
            items = gen.generate(min(pages * 10, 30), category_filter=keyword or None, source="zhilian")
            for it in items:
                it.source_url = it.source_url or f"{self.base_url}/jobs/{it.jd_id}.html"
            return items
        results: List[JDItem] = []
        for page in range(1, pages + 1):
            url = f"{self.base_url}/jobs/searchresult.ashx?kw={keyword}&p={page}"
            html = await self.fetch(url)
            if not html:
                continue
            for i, node in enumerate(self.parse(html)):
                try:
                    title = node.get("data-positionname", "") if hasattr(node, "attrs") else ""
                    company = node.get("data-companyname", "") if hasattr(node, "attrs") else ""
                    if not title:
                        t = node.select_one(".jobtitle__name")
                        title = t.get_text(strip=True) if t else ""
                    if not company:
                        c = node.select_one(".company__name")
                        company = c.get_text(strip=True) if c else ""
                    results.append(JDItem(
                        jd_id=self.make_jd_id("zl", page * 100 + i),
                        source=self.source_name,
                        source_url=url,
                        company=company,
                        title=title,
                    ))
                except Exception as e:  # noqa: BLE001
                    log.error(f"[ZhilianSpider] 解析失败: {e}")
        return results


# ============================================================
# 猎聘
# ============================================================
class LiepinSpider(BaseCrawler):
    """猎聘 JD 采集。"""

    source_name = "liepin"
    base_url = "https://www.liepin.com"

    async def crawl(self, keyword: str = "Python", pages: int = 1) -> List[JDItem]:
        log.info(f"[LiepinSpider] keyword={keyword} pages={pages}")
        if self.use_mock:
            from app.services.mock_data import MockJDGenerator
            gen = MockJDGenerator()
            items = gen.generate(min(pages * 10, 30), category_filter=keyword or None, source="liepin")
            for it in items:
                it.source_url = it.source_url or f"{self.base_url}/job/{it.jd_id}.html"
            return items
        results: List[JDItem] = []
        for page in range(1, pages + 1):
            url = f"{self.base_url}/zhaopin/?key={keyword}&curPage={page}"
            html = await self.fetch(url)
            if not html:
                continue
            for i, node in enumerate(self.parse(html)):
                try:
                    t = node.select_one(".ellipsis-1") if hasattr(node, "select_one") else None
                    title = t.get_text(strip=True) if t else ""
                    results.append(JDItem(
                        jd_id=self.make_jd_id("lp", page * 100 + i),
                        source=self.source_name,
                        source_url=url,
                        title=title,
                    ))
                except Exception as e:  # noqa: BLE001
                    log.error(f"[LiepinSpider] 解析失败: {e}")
        return results


# ============================================================
# 企业官网
# ============================================================
class EnterpriseSpider(BaseCrawler):
    """企业官网岗位描述采集（careers.* / jobs.* / join.*）。"""

    source_name = "enterprise"
    base_url = ""

    DEFAULT_TARGETS = [
        "https://www.bytedance.com/careers",
        "https://careers.tencent.com",
        "https://talent.alibaba.com",
        "https://join.ustc.edu.cn",
    ]

    async def crawl(self, keyword: str = "", pages: int = 1) -> List[JDItem]:
        log.info(f"[EnterpriseSpider] keyword={keyword} pages={pages}")
        if self.use_mock:
            from app.services.mock_data import MockJDGenerator
            gen = MockJDGenerator()
            return gen.generate(min(pages * 8, 25), category_filter=keyword or None, source="enterprise")
        results: List[JDItem] = []
        targets = self.DEFAULT_TARGETS[: max(1, pages)]
        for i, url in enumerate(targets, 1):
            html = await self.fetch(url)
            if not html:
                continue
            results.append(JDItem(
                jd_id=self.make_jd_id("ent", i),
                source=self.source_name,
                source_url=url,
                raw_text=html[:2000],
            ))
        return results


# ============================================================
# 行业研究报告
# ============================================================
class IndustryReportSpider(BaseCrawler):
    """行业研究报告采集（艾瑞 / 头豹 / 36氪 / 智库等）。"""

    source_name = "industry_report"
    base_url = "https://www.iresearch.com.cn"

    async def crawl(self, keyword: str = "AI", pages: int = 1) -> List[JDItem]:
        log.info(f"[IndustryReportSpider] keyword={keyword} pages={pages}")
        if self.use_mock:
            from app.services.mock_data import MockJDGenerator
            gen = MockJDGenerator()
            items = gen.generate(min(pages * 5, 15), category_filter="行业研究", source="industry_report")
            return items
        results: List[JDItem] = []
        for page in range(1, pages + 1):
            url = f"{self.base_url}/report?q={keyword}&page={page}"
            html = await self.fetch(url)
            if not html:
                continue
            for i, node in enumerate(self.parse(html)):
                try:
                    t = node.select_one(".report-title") if hasattr(node, "select_one") else None
                    title = t.get_text(strip=True) if t else ""
                    results.append(JDItem(
                        jd_id=self.make_jd_id("rep", page * 100 + i),
                        source=self.source_name,
                        source_url=url,
                        title=title,
                        category="行业研究",
                    ))
                except Exception as e:  # noqa: BLE001
                    log.error(f"[IndustryReportSpider] 解析失败: {e}")
        return results


# ============================================================
# 政策文件
# ============================================================
class PolicySpider(BaseCrawler):
    """政策文件采集（gov.cn / 各地人社局 / 工信部）。"""

    source_name = "policy"
    base_url = "http://www.gov.cn"

    async def crawl(self, keyword: str = "人工智能", pages: int = 1) -> List[JDItem]:
        log.info(f"[PolicySpider] keyword={keyword} pages={pages}")
        if self.use_mock:
            from app.services.mock_data import MockJDGenerator
            gen = MockJDGenerator()
            items = gen.generate(min(pages * 3, 10), category_filter="政策", source="policy")
            return items
        results: List[JDItem] = []
        for page in range(1, pages + 1):
            url = f"{self.base_url}/search/govsearch.htm?q={keyword}&t=zhengcelibrary_gw&page={page}"
            html = await self.fetch(url)
            if not html:
                continue
            for i, node in enumerate(self.parse(html)):
                try:
                    t = node.select_one("a") if hasattr(node, "select_one") else None
                    title = t.get_text(strip=True) if t else ""
                    results.append(JDItem(
                        jd_id=self.make_jd_id("pol", page * 100 + i),
                        source=self.source_name,
                        source_url=url,
                        title=title,
                        category="政策",
                    ))
                except Exception as e:  # noqa: BLE001
                    log.error(f"[PolicySpider] 解析失败: {e}")
        return results


# ============================================================
# O*NET / LinkedIn Skills
# ============================================================
class OnetSpider(BaseCrawler):
    """O*NET / LinkedIn Skills 数据采集。"""

    source_name = "onet"
    base_url = "https://www.onetonline.org"

    async def crawl(self, keyword: str = "", pages: int = 1) -> List[JDItem]:
        log.info(f"[OnetSpider] keyword={keyword} pages={pages}")
        if self.use_mock:
            from app.services.mock_data import MockJDGenerator
            gen = MockJDGenerator()
            return gen.generate(min(pages * 6, 20), category_filter="技能图谱", source="onet")
        results: List[JDItem] = []
        # O*NET 技能列表 API
        url = f"{self.base_url}/find/descriptor/result/2.A.1?keyword={keyword}"
        html = await self.fetch(url)
        if not html:
            return results
        for i, node in enumerate(self.parse(html)):
            try:
                t = node.select_one(".report-td") if hasattr(node, "select_one") else None
                title = t.get_text(strip=True) if t else ""
                results.append(JDItem(
                    jd_id=self.make_jd_id("onet", i),
                    source=self.source_name,
                    source_url=url,
                    title=title,
                    category="技能图谱",
                    skills=[title] if title else [],
                ))
            except Exception as e:  # noqa: BLE001
                log.error(f"[OnetSpider] 解析失败: {e}")
        return results


# ============================================================
# 统一 Spider 工厂
# ============================================================
SPIDER_REGISTRY = {
    "boss": BossSpider,
    "zhilian": ZhilianSpider,
    "liepin": LiepinSpider,
    "enterprise": EnterpriseSpider,
    "industry_report": IndustryReportSpider,
    "policy": PolicySpider,
    "onet": OnetSpider,
}


def get_spider(name: str, **kwargs) -> BaseCrawler:
    """工厂方法：根据名称获取 Spider 实例。"""
    cls = SPIDER_REGISTRY.get(name)
    if not cls:
        raise ValueError(f"未知 Spider: {name}，可选 {list(SPIDER_REGISTRY.keys())}")
    return cls(**kwargs)


async def crawl_all(keyword: str = "Python", pages: int = 1) -> Dict[str, List[JDItem]]:
    """并发执行所有 Spider，返回按来源分组的 JD 列表。"""
    tasks = {name: get_spider(name).crawl(keyword, pages) for name in SPIDER_REGISTRY}
    out: Dict[str, List[JDItem]] = {}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    for name, res in zip(tasks.keys(), results):
        if isinstance(res, Exception):
            log.error(f"Spider {name} 失败: {res}")
            out[name] = []
        else:
            out[name] = res
    return out


# ============================================================
# MockJDGenerator 重导出
# ============================================================
# mock_data 模块与 crawler 解耦：这里把 MockJDGenerator 暴露在 crawler 命名空间下，
# 方便 `from app.services.crawler import MockJDGenerator` 这类统一调用。
try:
    from app.services.mock_data import MockJDGenerator  # noqa: E402, F401
except Exception as e:  # noqa: BLE001
    log.warning(f"MockJDGenerator 延迟加载失败: {e}")
    MockJDGenerator = None  # type: ignore


__all__ = [
    "JDItem",
    "HTTPClient",
    "ProxyPool",
    "BaseCrawler",
    "BossSpider",
    "ZhilianSpider",
    "LiepinSpider",
    "EnterpriseSpider",
    "IndustryReportSpider",
    "PolicySpider",
    "OnetSpider",
    "SPIDER_REGISTRY",
    "get_spider",
    "crawl_all",
    "MockJDGenerator",
]
