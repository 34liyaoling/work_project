#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
独立数据采集工具 - 用于从多个数据源采集招聘信息

使用方式:
    python collector.py                          # 默认采集
    python collector.py --sources bing,zhipin    # 指定数据源
    python collector.py --output jobs.json       # 指定输出文件
    python collector.py --keywords 20            # 每个关键词采集数量
"""

import argparse
import json
import logging
import re
import time
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ===== 采集关键词 =====
JOB_KEYWORDS = [
    # 人工智能
    "AI算法工程师", "机器学习工程师", "深度学习工程师", "NLP算法工程师",
    "计算机视觉工程师", "推荐算法工程师", "大模型工程师", "LLM应用开发",
    "AI产品经理", "AI研究员", "语音算法工程师", "知识图谱工程师",
    # 大数据
    "数据分析师", "大数据开发工程师", "数据仓库工程师", "数据挖掘工程师",
    "数据科学家", "ETL工程师", "实时计算工程师", "Flink开发工程师",
    "Spark开发工程师", "数据治理工程师", "BI工程师", "数据运营",
    # 软件开发
    "Java开发工程师", "Python开发工程师", "Go开发工程师", "C++开发工程师",
    "C#开发工程师", "Rust开发工程师", "后端开发工程师", "全栈工程师",
    "架构师", "技术经理", "研发总监", "技术专家",
    # 前端开发
    "前端开发工程师", "Web前端工程师", "React开发工程师", "Vue开发工程师",
    "小程序开发工程师", "H5开发工程师", "前端架构师", "UI开发工程师",
    "Node.js开发工程师", "TypeScript开发工程师",
    # 移动开发
    "iOS开发工程师", "Android开发工程师", "Flutter开发工程师",
    "React Native开发工程师", "移动端开发工程师", "App开发工程师",
    # 云计算与DevOps
    "云计算工程师", "云架构师", "DevOps工程师", "SRE工程师",
    "运维开发工程师", "容器工程师", "K8s运维工程师", "云原生工程师",
    "基础设施工程师", "平台工程师", "自动化运维工程师",
    # 网络安全
    "网络安全工程师", "信息安全工程师", "渗透测试工程师", "安全运维工程师",
    "安全研究员", "安全架构师", "数据安全工程师", "安全分析师",
    "漏洞挖掘工程师", "应急响应工程师", "安全合规工程师",
    # 区块链与Web3
    "区块链开发工程师", "智能合约工程师", "Web3开发工程师",
    "Solidity开发工程师", "DeFi开发工程师", "区块链架构师",
    # 物联网与嵌入式
    "嵌入式开发工程师", "物联网工程师", "IoT开发工程师",
    "嵌入式软件工程师", "嵌入式硬件工程师", "驱动开发工程师",
    "RTOS开发工程师", "边缘计算工程师",
    # 测试与质量
    "测试工程师", "测试开发工程师", "自动化测试工程师",
    "性能测试工程师", "安全测试工程师", "QA工程师",
    # 产品与设计
    "产品经理", "数据产品经理", "技术产品经理", "UX设计师",
    "UI设计师", "交互设计师", "产品运营",
    # 数据库与中间件
    "数据库工程师", "DBA", "MySQL工程师", "PostgreSQL工程师",
    "MongoDB工程师", "Redis工程师", "Elasticsearch工程师",
    "消息队列工程师", "中间件工程师",
]


class BaseCollector:
    """采集器基类"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/125.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        self.request_delay = 0.5
    
    def collect(self, keyword: str, count: int = 10) -> list[dict]:
        """采集数据"""
        raise NotImplementedError


class BingCollector(BaseCollector):
    """Bing搜索引擎采集器"""
    
    name = "bing"
    
    def collect(self, keyword: str, count: int = 10) -> list[dict]:
        """从Bing搜索采集招聘信息"""
        jobs = []
        queries = [
            f'"{keyword}" 招聘',
            f'"{keyword}" 岗位要求 技能',
            f'{keyword} 招聘 北京',
        ]
        
        for query in queries:
            if len(jobs) >= count:
                break
            try:
                url = f"https://www.bing.com/search?q={quote_plus(query)}&count=20"
                time.sleep(self.request_delay)
                
                resp = self.session.get(url, timeout=15)
                resp.raise_for_status()
                
                # 解析搜索结果
                sections = resp.text.split('class="b_algo"')
                for section in sections[1:]:
                    if len(jobs) >= count:
                        break
                    
                    h2 = re.search(r'<h2[^>]*>([\s\S]*?)</h2>', section)
                    link_m = re.search(r'<a[^>]*href="(https?://[^"]*)"', section)
                    desc_m = re.search(r'<p[^>]*>([\s\S]*?)</p>', section)
                    
                    if not h2 or not link_m:
                        continue
                    
                    title = re.sub(r'<[^>]+>', '', h2.group(1)).strip()
                    link = link_m.group(1)
                    desc = re.sub(r'<[^>]+>', '', desc_m.group(1)).strip() if desc_m else ""
                    
                    if len(title) < 5 or len(title) > 100:
                        continue
                    
                    # 过滤非招聘相关
                    if not any(kw in title.lower() for kw in [
                        "招聘", "岗位", "工程师", "开发", "分析师", 
                        "架构师", "经理", "专家", "设计师"
                    ]):
                        continue
                    
                    jobs.append({
                        "job_title": title[:80],
                        "company_name": self._extract_company(title),
                        "salary_min": None,
                        "salary_max": None,
                        "location": self._extract_location(desc),
                        "skills": [],
                        "job_description": desc[:500] if desc else "",
                        "source": "bing_search",
                        "source_url": link,
                        "collected_at": datetime.now().isoformat(),
                    })
                
            except Exception as e:
                logger.warning(f"Bing采集失败 [{keyword}]: {e}")
                continue
        
        logger.info(f"Bing采集完成: {keyword} -> {len(jobs)}条")
        return jobs
    
    def _extract_company(self, title: str) -> str:
        """从标题提取公司名"""
        for site in ["BOSS直聘", "猎聘", "智联招聘", "前程无忧", "拉勾"]:
            if site in title:
                return site
        return ""
    
    def _extract_location(self, text: str) -> str:
        """从文本提取地点"""
        cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "南京", "武汉", "西安", "苏州"]
        for city in cities:
            if city in text:
                return city
        return ""


class DuckDuckGoCollector(BaseCollector):
    """DuckDuckGo搜索引擎采集器"""
    
    name = "duckduckgo"
    
    def collect(self, keyword: str, count: int = 10) -> list[dict]:
        """从DuckDuckGo搜索采集招聘信息"""
        jobs = []
        
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(f'{keyword} 招聘')}"
            time.sleep(self.request_delay)
            
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            
            sections = resp.text.split('class="result__body"')
            for section in sections[1:count+1]:
                h2 = re.search(r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([\s\S]*?)</a>', section)
                if not h2:
                    continue
                
                link = h2.group(1)
                title = re.sub(r'<[^>]+>', '', h2.group(2)).strip()
                
                if len(title) < 5 or len(title) > 100:
                    continue
                
                jobs.append({
                    "job_title": title[:80],
                    "company_name": "",
                    "salary_min": None,
                    "salary_max": None,
                    "location": "",
                    "skills": [],
                    "job_description": "",
                    "source": "duckduckgo_search",
                    "source_url": link,
                    "collected_at": datetime.now().isoformat(),
                })
            
        except Exception as e:
            logger.warning(f"DuckDuckGo采集失败 [{keyword}]: {e}")
        
        logger.info(f"DuckDuckGo采集完成: {keyword} -> {len(jobs)}条")
        return jobs


class ZhipinCollector(BaseCollector):
    """BOSS直聘采集器（需要登录）"""
    
    name = "zhipin"
    
    def __init__(self, cookies: str = ""):
        super().__init__()
        self.cookies = cookies
        if cookies:
            self.session.headers["Cookie"] = cookies
    
    def collect(self, keyword: str, count: int = 10) -> list[dict]:
        """从BOSS直聘采集（需要登录cookie）"""
        if not self.cookies:
            logger.warning("BOSS直聘需要登录cookie，跳过")
            return []
        
        jobs = []
        # TODO: 实现BOSS直聘采集逻辑
        # 需要用户提供登录后的cookie
        logger.info(f"BOSS直聘采集: {keyword} -> 需要配置cookie")
        return jobs


class LiepinCollector(BaseCollector):
    """猎聘采集器"""
    
    name = "liepin"
    
    def __init__(self, cookies: str = ""):
        super().__init__()
        self.cookies = cookies
    
    def collect(self, keyword: str, count: int = 10) -> list[dict]:
        """从猎聘采集"""
        if not self.cookies:
            logger.warning("猎聘需要登录cookie，跳过")
            return []
        
        jobs = []
        # TODO: 实现猎聘采集逻辑
        logger.info(f"猎聘采集: {keyword} -> 需要配置cookie")
        return jobs


class LagouCollector(BaseCollector):
    """拉勾采集器"""
    
    name = "lagou"
    
    def __init__(self, cookies: str = ""):
        super().__init__()
        self.cookies = cookies
    
    def collect(self, keyword: str, count: int = 10) -> list[dict]:
        """从拉勾采集"""
        if not self.cookies:
            logger.warning("拉勾需要登录cookie，跳过")
            return []
        
        jobs = []
        # TODO: 实现拉勾采集逻辑
        logger.info(f"拉勾采集: {keyword} -> 需要配置cookie")
        return jobs


class DataCollector:
    """数据采集主控制器"""
    
    COLLECTORS = {
        "bing": BingCollector,
        "duckduckgo": DuckDuckGoCollector,
        "zhipin": ZhipinCollector,
        "liepin": LiepinCollector,
        "lagou": LagouCollector,
    }
    
    def __init__(self, sources: list[str] = None, cookies: dict = None):
        self.sources = sources or ["bing", "duckduckgo"]
        self.cookies = cookies or {}
        self.collectors = {}
        
        for source in self.sources:
            if source in self.COLLECTORS:
                collector_class = self.COLLECTORS[source]
                cookie = self.cookies.get(source, "")
                if cookie:
                    self.collectors[source] = collector_class(cookies=cookie)
                else:
                    self.collectors[source] = collector_class()
    
    def collect_all(self, keywords: list[str] = None, count_per_keyword: int = 5) -> dict:
        """采集所有关键词的数据"""
        keywords = keywords or JOB_KEYWORDS
        all_jobs = []
        stats = {"by_source": {}, "by_keyword": {}}
        
        logger.info(f"开始采集，关键词数: {len(keywords)}, 数据源: {self.sources}")
        
        for keyword in keywords:
            keyword_jobs = []
            for source_name, collector in self.collectors.items():
                try:
                    jobs = collector.collect(keyword, count=count_per_keyword)
                    keyword_jobs.extend(jobs)
                    
                    if source_name not in stats["by_source"]:
                        stats["by_source"][source_name] = 0
                    stats["by_source"][source_name] += len(jobs)
                    
                except Exception as e:
                    logger.error(f"采集失败 [{source_name}] [{keyword}]: {e}")
            
            stats["by_keyword"][keyword] = len(keyword_jobs)
            all_jobs.extend(keyword_jobs)
            
            # 去重
            seen = set()
            unique_jobs = []
            for job in all_jobs:
                key = job["job_title"][:30]
                if key not in seen:
                    seen.add(key)
                    unique_jobs.append(job)
            all_jobs = unique_jobs
        
        result = {
            "collected_at": datetime.now().isoformat(),
            "total_count": len(all_jobs),
            "stats": stats,
            "jobs": all_jobs,
        }
        
        logger.info(f"采集完成，共 {len(all_jobs)} 条数据")
        return result
    
    def save_to_file(self, data: dict, output_path: str):
        """保存数据到文件"""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"数据已保存到: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="独立数据采集工具")
    parser.add_argument("--sources", type=str, default="bing,duckduckgo",
                        help="数据源，逗号分隔 (bing,duckduckgo,zhipin,liepin,lagou)")
    parser.add_argument("--output", type=str, default="collected_jobs.json",
                        help="输出文件路径")
    parser.add_argument("--keywords", type=int, default=None,
                        help="使用前N个关键词（默认全部）")
    parser.add_argument("--count", type=int, default=5,
                        help="每个关键词采集数量")
    parser.add_argument("--cookies", type=str, default="",
                        help="登录cookie文件路径（JSON格式）")
    
    args = parser.parse_args()
    
    # 解析数据源
    sources = [s.strip() for s in args.sources.split(",")]
    
    # 加载cookies
    cookies = {}
    if args.cookies:
        try:
            with open(args.cookies, "r", encoding="utf-8") as f:
                cookies = json.load(f)
        except Exception as e:
            logger.warning(f"加载cookie失败: {e}")
    
    # 选择关键词
    keywords = JOB_KEYWORDS[:args.keywords] if args.keywords else JOB_KEYWORDS
    
    # 创建采集器
    collector = DataCollector(sources=sources, cookies=cookies)
    
    # 执行采集
    data = collector.collect_all(keywords=keywords, count_per_keyword=args.count)
    
    # 保存结果
    collector.save_to_file(data, args.output)
    
    # 打印统计
    print(f"\n{'='*50}")
    print(f"采集完成!")
    print(f"{'='*50}")
    print(f"总数据量: {data['total_count']}")
    print(f"输出文件: {args.output}")
    print(f"\n按数据源统计:")
    for source, count in data["stats"]["by_source"].items():
        print(f"  {source}: {count}条")


if __name__ == "__main__":
    main()
