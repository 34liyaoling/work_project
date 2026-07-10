"""岗位爬虫工具 - 基于 Playwright 实现真实招聘网站数据抓取"""

import json
import logging
import re
import time
from datetime import datetime
from typing import Optional

from langchain_core.tools import BaseTool
from pydantic import Field

from config.settings import get_settings

logger = logging.getLogger(__name__)


class JobScraperTool(BaseTool):
    """岗位爬虫 - 从公开招聘网站采集真实岗位数据（需 Playwright）"""

    name: str = "job_scraper"
    description: str = "从互联网招聘网站抓取真实的岗位招聘信息"

    request_delay: float = Field(default=2.0, description="请求间隔（秒）")
    headless: bool = Field(default=True, description="是否使用无头浏览器")

    def _run(self, keyword: str, location: str = "全国", count: int = 10) -> str:
        """执行爬虫并返回结果文本"""
        try:
            jobs = self.scrape_jobs(keyword, location, count)
            if jobs:
                summary = f"## 岗位采集结果: {keyword} ({location})\n\n"
                summary += f"共采集到 {len(jobs)} 条岗位信息\n\n"
                for i, job in enumerate(jobs, 1):
                    skills_str = ", ".join(job.get("skills", [])[:8])
                    salary = ""
                    if job.get("salary_min") and job.get("salary_max"):
                        salary = f"{job['salary_min']}K-{job['salary_max']}K"
                    company = job.get("company_name", "未知名")
                    summary += (
                        f"### {i}. {job['job_title']}\n"
                        f"- **公司**: {company}\n"
                        f"- **薪资**: {salary or '面议'}\n"
                        f"- **地点**: {job.get('location', '未知')}\n"
                        f"- **技能**: {skills_str or '未提取'}\n"
                        f"- **来源**: {job.get('source', 'web')}\n\n"
                    )
                return summary

            return f"未找到「{keyword}」相关的岗位信息（请确保已安装 Playwright: playwright install chromium）"

        except Exception as e:
            logger.error(f"岗位爬取出错: {e}")
            return f"岗位爬取出错: {e}（提示：请运行 playwright install chromium 安装浏览器）"

    def scrape_jobs(self, keyword: str, location: str = "全国",
                    count: int = 15, use_playwright: bool = True) -> list[dict]:
        """从真实招聘网站采集岗位数据

        采集策略:
        1. Playwright 爬取 LinkedIn / Indeed（需要 playwright install chromium）
        """
        settings = get_settings()

        if not use_playwright or not settings.crawler.enable_playwright:
            logger.info("Playwright 爬虫未启用")
            return []

        all_jobs = []
        sources = [
            ("linkedin", self._scrape_linkedin),
            ("indeed", self._scrape_indeed),
        ]

        for source_name, scrape_func in sources:
            if len(all_jobs) >= count:
                break
            try:
                jobs = scrape_func(keyword, location, count - len(all_jobs))
                if jobs:
                    for job in jobs:
                        job["source"] = source_name
                    all_jobs.extend(jobs)
                    logger.info(f"从 {source_name} 采集到 {len(jobs)} 条数据")
            except Exception as e:
                logger.debug(f"从 {source_name} 采集失败: {e}")
                continue

        return all_jobs

    def _scrape_linkedin(self, keyword: str, location: str,
                         count: int) -> list[dict]:
        """从 LinkedIn 公开页面抓取岗位信息"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("Playwright 未安装，请运行: pip install playwright && playwright install chromium")
            raise

        jobs = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
            )
            page = context.new_page()

            try:
                url = f"https://www.linkedin.com/jobs/search/?keywords={keyword}"
                if location and location != "全国":
                    url += f"&location={location}"

                logger.info(f"正在访问 LinkedIn: {url}")
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(3)

                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(2)

                job_cards = page.query_selector_all(".job-search-card")
                if not job_cards:
                    job_cards = page.query_selector_all(".base-card")

                for card in job_cards[:count]:
                    try:
                        title_el = card.query_selector("h3")
                        company_el = card.query_selector(".base-search-card__subtitle")
                        location_el = card.query_selector(".job-search-card__location")

                        title = title_el.inner_text().strip() if title_el else keyword
                        company = company_el.inner_text().strip() if company_el else ""
                        loc = location_el.inner_text().strip() if location_el else location

                        jobs.append({
                            "job_title": title[:80],
                            "company_name": company[:50],
                            "location": loc[:30] if loc else location,
                            "skills": [],
                            "salary_min": None,
                            "salary_max": None,
                            "experience_min": None,
                            "experience_max": None,
                            "education": "",
                            "job_description": f"LinkedIn: {title} @ {company}",
                            "source_url": page.url,
                        })
                    except Exception:
                        continue

            except Exception as e:
                logger.error(f"LinkedIn 页面处理异常: {e}")
            finally:
                browser.close()

        return jobs

    def _scrape_indeed(self, keyword: str, location: str,
                       count: int) -> list[dict]:
        """从 Indeed 公开页面抓取岗位信息"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise

        jobs = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            try:
                query = f"{keyword}+{location}" if location != "全国" else keyword
                url = f"https://cn.indeed.com/jobs?q={query}"
                logger.info(f"正在访问 Indeed: {url}")

                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(2)

                job_cards = page.query_selector_all(".job_seen_beacon, .tapItem")

                for card in job_cards[:count]:
                    try:
                        title_el = card.query_selector("h2 a")
                        company_el = card.query_selector(".companyName")
                        location_el = card.query_selector(".companyLocation")
                        salary_el = card.query_selector(".salary-snippet")

                        title = title_el.inner_text().strip() if title_el else keyword
                        company = company_el.inner_text().strip() if company_el else ""
                        loc = location_el.inner_text().strip() if location_el else location
                        salary_text = salary_el.inner_text().strip() if salary_el else ""

                        salary_min, salary_max = self._parse_salary(salary_text)

                        jobs.append({
                            "job_title": title[:80],
                            "company_name": company[:50],
                            "location": loc[:30],
                            "skills": [],
                            "salary_min": salary_min,
                            "salary_max": salary_max,
                            "experience_min": None,
                            "experience_max": None,
                            "education": "",
                            "job_description": f"Indeed: {title} @ {company}",
                            "source_url": page.url,
                        })
                    except Exception:
                        continue

            except Exception as e:
                logger.error(f"Indeed 页面处理异常: {e}")
            finally:
                browser.close()

        return jobs

    def _parse_salary(self, salary_text: str) -> tuple:
        """解析薪资文本为数字范围"""
        if not salary_text:
            return None, None

        numbers = re.findall(r'(\d+\.?\d*)', salary_text.replace(",", ""))
        if len(numbers) >= 2:
            try:
                min_val = float(numbers[0])
                max_val = float(numbers[1])

                if "万" in salary_text and "年" in salary_text:
                    min_val = min_val / 12 * 10
                    max_val = max_val / 12 * 10
                elif "万" in salary_text:
                    min_val = min_val * 10
                    max_val = max_val * 10

                return int(min_val), int(max_val)
            except ValueError:
                pass
        elif len(numbers) == 1:
            try:
                val = float(numbers[0])
                return int(val), int(val * 1.3)
            except ValueError:
                pass

        return None, None

    def validate_url(self, url: str) -> bool:
        """验证URL是否可访问"""
        try:
            import requests
            resp = requests.head(url, timeout=5,
                                 headers={"User-Agent": "Mozilla/5.0"})
            return resp.status_code < 400
        except Exception:
            return False
