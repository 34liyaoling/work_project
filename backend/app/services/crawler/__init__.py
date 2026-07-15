"""爬虫模块 - 包入口

本子包为 XH-202621 岗位/能力图谱系统提供多源异构数据采集能力：

* :mod:`base`         - 抽象基类 :class:`BaseCrawler`，统一 fetch / parse / save 接口
* :mod:`proxy_pool`   - 代理池（动态切换 + 健康检查）
* :mod:`boss_spider`  - BOSS直聘 Spider
* :mod:`zhilian_spider` - 智联招聘 Spider
* :mod:`liepin_spider`  - 猎聘 Spider
* :mod:`playwright_crawler` - 动态页面渲染（企业官网，对外别名 ``EnterpriseSpider``）
* :mod:`industry_reports` - 行业研究报告 / 政策文件
* :mod:`onet_crawler`  - O*NET / LinkedIn Skills
* :mod:`pipeline`      - Scrapy-style 调度管道（去重、清洗、入库）

所有 Spider 默认开启 ``use_mock=True`` 模式：当目标站点不可达或离线时，
从 :mod:`app.services.mock_data` 拉取真实风格的样例 JD，
保证端到端流程在受限环境下也能跑通。

为保持向后兼容，本包同时导出旧 ``crawler.py`` 提供的类名：
``HTTPClient``、``EnterpriseSpider``、``crawl_all``、``SPIDER_REGISTRY``、``get_spider`` 等。
"""
from __future__ import annotations

import asyncio
from typing import Dict, List

# 优先从子模块导入主要符号
from app.services.crawler.base import (
    BaseCrawler,
    JDItem,
    DEFAULT_USER_AGENTS,
)
from app.services.crawler.proxy_pool import ProxyPool, get_default_proxy_pool
from app.services.crawler.boss_spider import BossSpider
from app.services.crawler.zhilian_spider import ZhilianSpider
from app.services.crawler.liepin_spider import LiepinSpider
from app.services.crawler.playwright_crawler import PlaywrightCrawler
from app.services.crawler.industry_reports import IndustryReportSpider, PolicySpider
from app.services.crawler.onet_crawler import OnetSpider
from app.services.crawler.pipeline import CrawlPipeline, PipelineContext

# Spider 注册表：方便统一调度
SPIDER_REGISTRY = {
    "boss": BossSpider,
    "zhilian": ZhilianSpider,
    "liepin": LiepinSpider,
    "enterprise": PlaywrightCrawler,
    "industry_report": IndustryReportSpider,
    "policy": PolicySpider,
    "onet": OnetSpider,
}


def get_spider(name: str, **kwargs):
    """工厂方法：按名称获取 Spider 实例"""
    cls = SPIDER_REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"未知 Spider: {name}，可选 {list(SPIDER_REGISTRY.keys())}")
    return cls(**kwargs)


async def crawl_all(keyword: str = "Python", pages: int = 1) -> Dict[str, List[JDItem]]:
    """并发执行所有 Spider，返回 ``{source: [items]}``"""
    tasks: Dict[str, "asyncio.Future"] = {}
    for name in SPIDER_REGISTRY:
        tasks[name] = asyncio.create_task(
            get_spider(name).crawl(keyword, pages)
        )
    results: Dict[str, List[JDItem]] = {}
    for name, t in tasks.items():
        try:
            results[name] = await t
        except Exception as e:  # noqa: BLE001
            from app.core.logger import log
            log.error(f"crawl_all: {name} 失败: {e}")
            results[name] = []
    return results


# ============================================================
# 向后兼容：旧 crawler.py 中提供的类 / 函数别名
# ============================================================
# :class:`EnterpriseSpider` 旧类名（用 :class:`PlaywrightCrawler` 替代）
EnterpriseSpider = PlaywrightCrawler


# :class:`HTTPClient` 旧 HTTP 客户端
# 这里把 HTTPClient 实现为 BaseCrawler.request_with_retry 的封装类。
class HTTPClient:
    """通用 HTTP 客户端（旧版兼容名）。

    主要职责：
        * UA 轮换
        * 频率控制
        * 代理池支持
        * 自动重试
    """

    DEFAULT_UAS = DEFAULT_USER_AGENTS

    def __init__(
        self,
        ua: str = "",
        proxies: "ProxyPool" = None,
        min_interval: float = 1.0,
        max_interval: float = 3.0,
        timeout: float = 15.0,
        max_retries: int = 3,
    ) -> None:
        self.ua = ua
        self.proxies = proxies or get_default_proxy_pool()
        self.min_interval = float(min_interval)
        self.max_interval = float(max_interval)
        self.timeout = float(timeout)
        self.max_retries = int(max_retries)

    def get_ua(self) -> str:
        if self.ua:
            return self.ua
        return BaseCrawler.pick_ua(self)

    async def get(self, url: str) -> str:
        """GET 一个 URL，返回 HTML 文本"""
        # 借助 BaseCrawler 复用限频 / 重试 / 代理
        bc = BaseCrawler(
            use_mock=False,
            min_interval=self.min_interval,
            max_interval=self.max_interval,
            max_retries=self.max_retries,
            timeout=self.timeout,
            proxies=self.proxies,
        )
        return await bc.request_with_retry(url) or ""

    @staticmethod
    def parse_html(html: str, selector: str = ""):
        """对外静态方法：解析 HTML"""
        return BaseCrawler.parse_html(html, selector)


__all__ = [
    # 数据结构
    "JDItem",
    "DEFAULT_USER_AGENTS",
    # 基类
    "BaseCrawler",
    "HTTPClient",
    # 工具
    "ProxyPool",
    "get_default_proxy_pool",
    # Spider
    "BossSpider",
    "ZhilianSpider",
    "LiepinSpider",
    "PlaywrightCrawler",
    "EnterpriseSpider",
    "IndustryReportSpider",
    "PolicySpider",
    "OnetSpider",
    # 调度
    "CrawlPipeline",
    "PipelineContext",
    "SPIDER_REGISTRY",
    "get_spider",
    "crawl_all",
]
