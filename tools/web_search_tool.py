"""Web搜索工具 - 仅使用真实搜索引擎，无任何硬编码演示数据"""

import json
import logging
import re
import time
from typing import Optional
from urllib.parse import quote_plus

import requests
from langchain_core.tools import BaseTool
from pydantic import Field

from config.settings import get_settings

logger = logging.getLogger(__name__)

# 招聘网站URL关键词过滤列表（仅用于URL类型标记，不用于兜底）
JOB_SITE_KEYWORDS = [
    'zhipin.com', 'lagou.com', 'liepin.com', '51job.com', 'zhaopin.com',
    'bosszhipin', 'kanzhun', 'maimai', 'jobui',
]

# 搜索引擎配置
SEARCH_ENGINES = [
    {
        "name": "Bing",
        "url": "https://www.bing.com/search?q={query}&count=20",
    },
    {
        "name": "DuckDuckGo",
        "url": "https://html.duckduckgo.com/html/?q={query}",
    },
]


class WebSearchTool(BaseTool):
    """网络搜索工具 - 从真实搜索引擎获取技术信息和岗位数据"""
    name: str = "web_search"
    description: str = "搜索互联网上的最新信息，用于了解技术趋势、行业动态、岗位需求等"

    request_delay: float = Field(default=0.3, description="请求间隔（秒）")

    def _run(self, query: str, num_results: int = 5) -> str:
        """执行搜索引擎搜索"""
        for engine in SEARCH_ENGINES:
            try:
                if engine["name"] == "Bing":
                    results = self._search_bing(query, num_results)
                else:
                    results = self._search_duckduckgo(query, num_results)
                if results:
                    return results
            except Exception as e:
                logger.debug(f"{engine['name']}搜索失败: {e}")
                continue

        return f"## 搜索「{query}」未找到结果\n\n未从任何搜索引擎获取到有效信息"

    def _search_bing(self, query: str, num_results: int) -> str:
        """使用 Bing 搜索"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/125.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        url = f"https://www.bing.com/search?q={quote_plus(query)}&count={num_results + 5}"
        time.sleep(self.request_delay)

        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        results = []
        for match in re.finditer(
            r'<li class="b_algo">[\s\S]*?<a[^>]*href="([^"]*)"[^>]*>([\s\S]*?)</a>'
            r'[\s\S]*?<p[^>]*>([\s\S]*?)</p>',
            resp.text
        ):
            link = match.group(1)
            title = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            snippet = re.sub(r'<[^>]+>', '', match.group(3)).strip()
            results.append(f"- [{title}]({link})\n  {snippet[:200]}")
            if len(results) >= num_results:
                break

        if not results:
            all_links = re.findall(
                r'<a[^>]*href="(https?://[^"]+)"[^>]*>([\s\S]*?)</a>',
                resp.text
            )
            for link, title in all_links[:num_results]:
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                if clean_title and len(clean_title) > 5:
                    results.append(f"- [{clean_title[:80]}]({link})")

        if results:
            return (f"## 搜索「{query}」结果（来源: Bing）\n\n"
                    + "\n\n".join(results))
        raise Exception("Bing未返回任何结果")

    def _search_duckduckgo(self, query: str, num_results: int) -> str:
        """使用 DuckDuckGo 搜索"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        time.sleep(self.request_delay)

        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        results = []
        for match in re.finditer(
            r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([\s\S]*?)</a>'
            r'[\s\S]*?<a[^>]*class="result__snippet"[^>]*>([\s\S]*?)</a>',
            resp.text
        ):
            link = match.group(1)
            title = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            snippet = re.sub(r'<[^>]+>', '', match.group(3)).strip()
            results.append(f"- [{title}]({link})\n  {snippet[:200]}")
            if len(results) >= num_results:
                break

        if results:
            return (f"## 搜索「{query}」结果（来源: DuckDuckGo）\n\n"
                    + "\n\n".join(results))
        raise Exception("DuckDuckGo未返回任何结果")

    def search_jobs(self, keyword: str, location: str = "全国", count: int = 10) -> list[dict]:
        """从搜索引擎搜索真实招聘信息，返回结构化数据

        Args:
            keyword: 搜索关键词，如 "AI算法工程师"
            location: 地点，如 "北京"
            count: 最多返回条数

        Returns:
            包含 job_title, source_url, source, job_description 的列表
        """
        # 使用更精准的搜索词：加引号精确匹配
        search_queries = [
            f'"{keyword}" "招聘"',
            f'"{keyword}" 岗位要求 技能',
            f'{keyword} 招聘 {location}',
        ]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/125.0.0.0 Safari/537.36",
        }

        jobs = []
        seen_titles = set()

        for query in search_queries:
            if len(jobs) >= count:
                break
            try:
                url = f"https://www.bing.com/search?q={quote_plus(query)}&count=20"
                time.sleep(self.request_delay)

                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                text = resp.text

                # 解析b_algo区块
                sections = text.split('class="b_algo"')
                for section in sections[1:]:
                    if len(jobs) >= count:
                        break

                    h2 = re.search(r'<h2[^>]*>([\s\S]*?)</h2>', section)
                    link_m = re.search(r'<a[^>]*href="(https?://[^"]*)"', section)
                    if not h2 or not link_m:
                        continue

                    title = re.sub(r'<[^>]+>', '', h2.group(1)).strip()
                    link = link_m.group(1)

                    if not title or len(title) < 5 or len(title) > 100:
                        continue

                    title_lower = title.lower()
                    if not any(kw in title_lower for kw in [
                        "招聘", "岗位", "工程师", "开发", "实习", "数据分析",
                        "算法", "架构师", "经理", "专家", "科学家"
                    ]):
                        continue

                    dedup_key = title[:20]
                    if dedup_key in seen_titles:
                        continue
                    seen_titles.add(dedup_key)

                    is_job_site = any(domain in link.lower() for domain in JOB_SITE_KEYWORDS)

                    company_name = ""
                    for site in ["BOSS直聘", "猎聘", "智联招聘", "前程无忧"]:
                        if site in title:
                            company_name = site
                            break

                    jobs.append({
                        "job_title": title.strip()[:80],
                        "source_url": link,
                        "source": "bing_search",
                        "job_description": title.strip(),
                        "is_job_site": is_job_site,
                        "skills": [],
                        "salary_min": None,
                        "salary_max": None,
                        "location": location if location != "全国" else "",
                        "company_name": company_name,
                    })

            except requests.RequestException as e:
                logger.debug(f"Bing搜索失败 [{query[:20]}]: {e}")
                continue
            except Exception as e:
                logger.debug(f"搜索异常 [{query[:20]}]: {e}")
                continue

        if jobs:
            job_site_count = sum(1 for j in jobs if j["is_job_site"])
            logger.info(f"从Bing搜索到 {len(jobs)} 条招聘信息（其中 {job_site_count} 条来自招聘网站）")
            return jobs

        # 备用：尝试DuckDuckGo
        try:
            logger.info(f"Bing未返回结果，尝试DuckDuckGo搜索: {keyword}")
            ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(f'\"{keyword}\" \"招聘\"')}"
            time.sleep(self.request_delay)
            resp = requests.get(ddg_url, headers=headers, timeout=15)
            resp.raise_for_status()

            sections = resp.text.split('class="result__body"')
            for section in sections[1:]:
                if len(jobs) >= count:
                    break
                h2 = re.search(r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([\s\S]*?)</a>', section)
                if not h2:
                    continue
                link = h2.group(1)
                title = re.sub(r'<[^>]+>', '', h2.group(2)).strip()
                if not title or len(title) < 5 or len(title) > 100:
                    continue
                if not any(kw in title.lower() for kw in ["招聘","岗位","工程师","开发","算法","架构师"]):
                    continue
                dedup_key = title[:20]
                if dedup_key in seen_titles:
                    continue
                seen_titles.add(dedup_key)
                jobs.append({
                    "job_title": title.strip()[:80],
                    "source_url": link,
                    "source": "duckduckgo_search",
                    "job_description": title.strip(),
                    "is_job_site": any(d in link.lower() for d in JOB_SITE_KEYWORDS),
                    "skills": [],
                    "salary_min": None, "salary_max": None,
                    "location": "", "company_name": "",
                })

            if jobs:
                logger.info(f"从DuckDuckGo搜索到 {len(jobs)} 条招聘信息")
                return jobs
        except Exception as e:
            logger.debug(f"DuckDuckGo搜索失败: {e}")

        logger.warning(f"所有搜索引擎均未搜索到「{keyword}」相关招聘信息")
        return jobs

    def search_jobs_multiple_keywords(self, keywords: list[str], count_per_keyword: int = 5) -> list[dict]:
        """批量搜索多个关键词的招聘信息，去重后返回

        Args:
            keywords: 搜索关键词列表
            count_per_keyword: 每个关键词最多返回数

        Returns:
            合并去重后的招聘信息列表
        """
        all_jobs = []
        seen_titles = set()

        for keyword in keywords:
            jobs = self.search_jobs(keyword, "全国", count_per_keyword)
            for job in jobs:
                dedup_key = job["job_title"][:20]
                if dedup_key not in seen_titles:
                    seen_titles.add(dedup_key)
                    job["search_keyword"] = keyword
                    all_jobs.append(job)
            time.sleep(self.request_delay)

        logger.info(f"多关键词搜索完成: {len(keywords)}个关键词 → {len(all_jobs)}条招聘信息")
        return all_jobs

    def _is_job_site_url(self, url: str) -> bool:
        """判断URL是否为招聘网站链接"""
        url_lower = url.lower()
        for keyword in JOB_SITE_KEYWORDS:
            if keyword in url_lower:
                return True
        return False

    def fetch_page_content(self, url: str, timeout: int = 15) -> Optional[str]:
        """获取指定URL的页面内容"""
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            logger.debug(f"获取页面失败 [{url}]: {e}")
            return None
