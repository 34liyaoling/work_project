"""Playwright 动态页面采集器（企业官网）

适用场景：
    * 字节跳动 careers / 腾讯招聘 / 阿里 talent 等企业官网
    * 强反爬 / 强 JS 渲染场景

特性：
    * 模拟真人：UA 轮换 + viewport 随机化 + 鼠标轨迹 + 滚动
    * 失败时回退 mock
    * 未安装 playwright 时安全降级
"""
from __future__ import annotations

import asyncio
import random
from typing import Any, Dict, List, Optional

from app.core.logger import log
from app.services.crawler.base import BaseCrawler, JDItem, DEFAULT_USER_AGENTS


# Playwright 软依赖
try:
    from playwright.async_api import async_playwright  # type: ignore
    HAS_PLAYWRIGHT = True
except Exception:  # noqa: BLE001
    HAS_PLAYWRIGHT = False


class PlaywrightCrawler(BaseCrawler):
    """企业官网动态渲染采集"""

    source_name: str = "enterprise"
    base_url: str = ""

    # 默认目标列表（在线模式时遍历）
    DEFAULT_TARGETS: List[str] = [
        "https://www.bytedance.com/careers",
        "https://careers.tencent.com",
        "https://talent.alibaba.com",
        "https://join.ustc.edu.cn",
    ]

    def __init__(
        self,
        *args,
        scroll: bool = True,
        wait_ms: int = 1500,
        viewport_pool: Optional[List[Dict[str, int]]] = None,
        headless: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.scroll = bool(scroll)
        self.wait_ms = int(wait_ms)
        self.headless = bool(headless)
        self.viewport_pool = viewport_pool or [
            {"width": 1366, "height": 768},
            {"width": 1440, "height": 900},
            {"width": 1536, "height": 864},
            {"width": 1680, "height": 1050},
        ]

    # -------------------------------------------------------- 抽象实现
    async def fetch(self, url: str) -> Optional[str]:
        """用 Playwright 抓取动态页面，返回可见文本"""
        if not HAS_PLAYWRIGHT:
            log.warning("Playwright 未安装，无法执行动态页面抓取")
            return None
        await self.throttle()
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                ctx = await browser.new_context(
                    user_agent=random.choice(DEFAULT_USER_AGENTS),
                    viewport=random.choice(self.viewport_pool),
                    locale="zh-CN",
                )
                page = await ctx.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                # 模拟真人：随机等待 + 滚动
                await page.wait_for_timeout(self.wait_ms + random.randint(0, 800))
                if self.scroll:
                    await page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight / 2)"
                    )
                    await page.wait_for_timeout(500)
                text = await page.inner_text("body")
                await browser.close()
                return text[:5000]
        except Exception as e:  # noqa: BLE001
            log.error(f"[PlaywrightCrawler] 抓取 {url} 失败: {e}")
            return None

    def parse(self, html: str, **kwargs) -> List[JDItem]:
        """从可见文本中切分 JD 段落（启发式）

        启发式：以空行分段，保留长度适中的非空段作为 JD 文本
        """
        items: List[JDItem] = []
        if not html:
            return items
        chunks = [c.strip() for c in html.split("\n\n") if c.strip()]
        idx = 0
        for chunk in chunks:
            if 80 <= len(chunk) <= 2000 and any(
                kw in chunk for kw in ["职责", "要求", "Engineer", "Developer", "工作"]
            ):
                items.append(JDItem(
                    jd_id=self.make_jd_id("ent", idx),
                    source=self.source_name,
                    source_url=kwargs.get("url", ""),
                    raw_text=chunk,
                    title=self._guess_title(chunk),
                ))
                idx += 1
                if idx >= 20:
                    break
        return items

    @staticmethod
    def _guess_title(chunk: str) -> str:
        for line in chunk.splitlines():
            line = line.strip()
            if 4 <= len(line) <= 60 and any(
                kw in line for kw in ["工程师", "研发", "开发", "Manager", "Engineer"]
            ):
                return line
        return chunk.splitlines()[0][:60] if chunk else "未知岗位"

    # -------------------------------------------------------- 主流程
    async def crawl(self, keyword: str = "", pages: int = 1) -> List[JDItem]:
        log.info(f"[PlaywrightCrawler] keyword={keyword} pages={pages} use_mock={self.use_mock}")
        if self.use_mock:
            return self._crawl_mock(keyword, pages)
        targets = self.DEFAULT_TARGETS[: max(1, pages)]
        all_items: List[JDItem] = []
        for url in targets:
            text = await self.fetch(url)
            if not text:
                continue
            all_items.extend(self.parse(text, url=url))
        return self.save(all_items)


# 同步便捷入口（与 :mod:`risk_handler` 兼容）
def human_like_browse(url: str, scroll: bool = True, wait_ms: int = 1500) -> Dict[str, Any]:
    """同步便捷函数：用于在已有事件循环中无法 await 的场景"""
    if not HAS_PLAYWRIGHT:
        return {"status": -1, "text": "", "error": "playwright not installed"}
    try:
        from playwright.sync_api import sync_playwright
    except Exception:  # noqa: BLE001
        return {"status": -1, "text": "", "error": "playwright not installed"}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=random.choice(DEFAULT_USER_AGENTS),
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
        return {"status": -1, "text": "", "error": str(e)}


__all__ = ["PlaywrightCrawler", "human_like_browse", "HAS_PLAYWRIGHT"]
