"""智联招聘 Spider

数据源：https://www.zhaopin.com
反爬要点：
    * UA 轮换
    * 随机延时 1.5~3s（智联风控比 BOSS 稍弱）
    * 默认走 mock
"""
from __future__ import annotations

from typing import List, Optional

from app.core.logger import log
from app.services.crawler.base import BaseCrawler, JDItem


class ZhilianSpider(BaseCrawler):
    """智联招聘 JD 采集"""

    source_name: str = "zhilian"
    base_url: str = "https://www.zhaopin.com"

    LIST_URL = "https://www.zhaopin.com/jobs/searchresult.ashx"
    CARD_SELECTOR = "div.joblist-box > div.job-primary"
    TITLE_SELECTOR = ".jobtitle__name"
    COMPANY_SELECTOR = ".company__name"
    SALARY_SELECTOR = ".job__salary"

    async def fetch(self, url: str) -> Optional[str]:
        return await self.request_with_retry(url)

    def parse(self, html: str, **kwargs) -> List[JDItem]:
        items: List[JDItem] = []
        for i, node in enumerate(self.parse_html(html, self.CARD_SELECTOR)):
            try:
                title = ""
                company = ""
                salary = ""
                # 智联部分节点用 data-* 属性
                if hasattr(node, "attrs"):
                    title = node.attrs.get("data-positionname", "") or title
                    company = node.attrs.get("data-companyname", "") or company
                t = node.select_one(self.TITLE_SELECTOR) if hasattr(node, "select_one") else None
                c = node.select_one(self.COMPANY_SELECTOR) if hasattr(node, "select_one") else None
                s = node.select_one(self.SALARY_SELECTOR) if hasattr(node, "select_one") else None
                if t:
                    title = t.get_text(strip=True)
                if c:
                    company = c.get_text(strip=True)
                if s:
                    salary = self.salary_normalize(s.get_text(strip=True))
                items.append(JDItem(
                    jd_id=self.make_jd_id("zl", i),
                    source=self.source_name,
                    source_url=kwargs.get("page_url", ""),
                    title=title,
                    company=company,
                    salary_range=salary,
                    raw_text=str(node)[:2000],
                ))
            except Exception as e:  # noqa: BLE001
                log.error(f"[ZhilianSpider] 解析第 {i} 张卡片失败: {e}")
        return items

    async def crawl(self, keyword: str = "Python", pages: int = 1) -> List[JDItem]:
        log.info(f"[ZhilianSpider] keyword={keyword} pages={pages} use_mock={self.use_mock}")
        if self.use_mock:
            return self._crawl_mock(keyword, pages)
        all_items: List[JDItem] = []
        for page in range(1, pages + 1):
            url = f"{self.LIST_URL}?kw={keyword}&p={page}"
            html = await self.fetch(url)
            if not html:
                continue
            all_items.extend(self.parse(html, page_url=url))
        return self.save(all_items)


__all__ = ["ZhilianSpider"]
