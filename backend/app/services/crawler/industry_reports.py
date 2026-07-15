"""行业报告与政策文件采集

包括：
* :class:`IndustryReportSpider`  - 行业研究报告（艾瑞 / 头豹 / 36氪 / 智库）
* :class:`PolicySpider`          - 政策文件（gov.cn / 各地人社局 / 工信部）

这些"非结构化文档"用于补充岗位宏观背景：行业趋势、政策导向、薪酬指数等。
"""
from __future__ import annotations

from typing import List, Optional

from app.core.logger import log
from app.services.crawler.base import BaseCrawler, JDItem


class IndustryReportSpider(BaseCrawler):
    """行业研究报告采集"""

    source_name: str = "industry_report"
    base_url: str = "https://www.iresearch.com.cn"

    LIST_URL = "https://www.iresearch.com.cn/report"
    CARD_SELECTOR = "div.report-item"
    TITLE_SELECTOR = ".report-title"
    PUBLISHER_SELECTOR = ".report-publisher"
    DATE_SELECTOR = ".report-date"

    async def fetch(self, url: str) -> Optional[str]:
        return await self.request_with_retry(url)

    def parse(self, html: str, **kwargs) -> List[JDItem]:
        items: List[JDItem] = []
        for i, node in enumerate(self.parse_html(html, self.CARD_SELECTOR)):
            try:
                t = node.select_one(self.TITLE_SELECTOR) if hasattr(node, "select_one") else None
                pub = node.select_one(self.PUBLISHER_SELECTOR) if hasattr(node, "select_one") else None
                d = node.select_one(self.DATE_SELECTOR) if hasattr(node, "select_one") else None
                title = t.get_text(strip=True) if t else ""
                publisher = pub.get_text(strip=True) if pub else ""
                date = d.get_text(strip=True) if d else None
                items.append(JDItem(
                    jd_id=self.make_jd_id("rep", i),
                    source=self.source_name,
                    source_url=kwargs.get("page_url", ""),
                    title=title,
                    company=publisher,
                    category="行业研究",
                    published_at=date,
                    raw_text=str(node)[:2000],
                ))
            except Exception as e:  # noqa: BLE001
                log.error(f"[IndustryReportSpider] 解析第 {i} 失败: {e}")
        return items

    async def crawl(self, keyword: str = "AI", pages: int = 1) -> List[JDItem]:
        log.info(f"[IndustryReportSpider] keyword={keyword} pages={pages} use_mock={self.use_mock}")
        if self.use_mock:
            return self._crawl_mock(keyword, pages)
        all_items: List[JDItem] = []
        for page in range(1, pages + 1):
            url = f"{self.LIST_URL}?q={keyword}&page={page}"
            html = await self.fetch(url)
            if not html:
                continue
            all_items.extend(self.parse(html, page_url=url))
        return self.save(all_items)


class PolicySpider(BaseCrawler):
    """政策文件采集"""

    source_name: str = "policy"
    base_url: str = "http://www.gov.cn"

    LIST_URL = "http://www.gov.cn/search/govsearch.htm"
    CARD_SELECTOR = "div.result"
    TITLE_SELECTOR = "a"
    DATE_SELECTOR = ".date"

    async def fetch(self, url: str) -> Optional[str]:
        return await self.request_with_retry(url)

    def parse(self, html: str, **kwargs) -> List[JDItem]:
        items: List[JDItem] = []
        for i, node in enumerate(self.parse_html(html, self.CARD_SELECTOR)):
            try:
                t = node.select_one(self.TITLE_SELECTOR) if hasattr(node, "select_one") else None
                d = node.select_one(self.DATE_SELECTOR) if hasattr(node, "select_one") else None
                title = t.get_text(strip=True) if t else ""
                date = d.get_text(strip=True) if d else None
                items.append(JDItem(
                    jd_id=self.make_jd_id("pol", i),
                    source=self.source_name,
                    source_url=kwargs.get("page_url", ""),
                    title=title,
                    category="政策",
                    published_at=date,
                    raw_text=str(node)[:2000],
                ))
            except Exception as e:  # noqa: BLE001
                log.error(f"[PolicySpider] 解析第 {i} 失败: {e}")
        return items

    async def crawl(self, keyword: str = "人工智能", pages: int = 1) -> List[JDItem]:
        log.info(f"[PolicySpider] keyword={keyword} pages={pages} use_mock={self.use_mock}")
        if self.use_mock:
            return self._crawl_mock(keyword, pages)
        all_items: List[JDItem] = []
        for page in range(1, pages + 1):
            url = f"{self.LIST_URL}?q={keyword}&t=zhengcelibrary_gw&page={page}"
            html = await self.fetch(url)
            if not html:
                continue
            all_items.extend(self.parse(html, page_url=url))
        return self.save(all_items)


__all__ = ["IndustryReportSpider", "PolicySpider"]
