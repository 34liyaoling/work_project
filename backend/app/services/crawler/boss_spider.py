"""BOSS直聘 Spider

数据源：https://www.zhipin.com
目标字段：岗位标题 / 公司 / 薪资 / 地点 / 描述
反爬要点：
    * UA 轮换
    * 随机延时 1~3s
    * 失败指数退避重试
    * 默认走 mock（避免被风控）
"""
from __future__ import annotations

from typing import List, Optional

from app.core.logger import log
from app.services.crawler.base import BaseCrawler, JDItem


class BossSpider(BaseCrawler):
    """BOSS直聘 JD 采集"""

    source_name: str = "boss"
    base_url: str = "https://www.zhipin.com"

    # BOSS 直聘 JD 列表的典型 CSS 选择器（在线模式时使用）
    LIST_URL = "https://www.zhipin.com/web/geek/job"
    CARD_SELECTOR = "li.job-card-wrapper"
    TITLE_SELECTOR = ".job-name"
    COMPANY_SELECTOR = ".company-name a"
    SALARY_SELECTOR = ".salary"
    LOCATION_SELECTOR = ".job-area"

    async def fetch(self, url: str) -> Optional[str]:
        """带反爬的 GET"""
        return await self.request_with_retry(url)

    def parse(self, html: str, **kwargs) -> List[JDItem]:
        """从 BOSS 直聘列表页抽取 JDItem 列表"""
        items: List[JDItem] = []
        nodes = self.parse_html(html, self.CARD_SELECTOR)
        for i, node in enumerate(nodes):
            try:
                title_el = node.select_one(self.TITLE_SELECTOR)
                company_el = node.select_one(self.COMPANY_SELECTOR)
                salary_el = node.select_one(self.SALARY_SELECTOR)
                loc_el = node.select_one(self.LOCATION_SELECTOR)
                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                salary = self.salary_normalize(
                    salary_el.get_text(strip=True) if salary_el else ""
                )
                location = loc_el.get_text(strip=True) if loc_el else ""
                items.append(JDItem(
                    jd_id=self.make_jd_id("boss", i),
                    source=self.source_name,
                    source_url=kwargs.get("page_url", ""),
                    company=company,
                    title=title,
                    salary_range=salary,
                    location=location,
                    raw_text=str(node)[:2000],
                ))
            except Exception as e:  # noqa: BLE001
                log.error(f"[BossSpider] 解析第 {i} 张卡片失败: {e}")
        return items

    async def crawl(self, keyword: str = "Python", pages: int = 1) -> List[JDItem]:
        """主流程：在线时按页抓取，失败时回退 mock"""
        log.info(f"[BossSpider] keyword={keyword} pages={pages} use_mock={self.use_mock}")
        if self.use_mock:
            return self._crawl_mock(keyword, pages)
        all_items: List[JDItem] = []
        for page in range(1, pages + 1):
            url = f"{self.LIST_URL}?query={keyword}&page={page}"
            html = await self.fetch(url)
            if not html:
                continue
            all_items.extend(self.parse(html, page_url=url))
        return self.save(all_items)


__all__ = ["BossSpider"]
