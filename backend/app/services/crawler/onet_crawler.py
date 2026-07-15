"""O*NET / LinkedIn Skills 数据采集

O*NET 是美国劳工部发布的职业数据库，包含：
* 职业描述、任务、工具、技术
* 技能、知识、能力分类

LinkedIn Skills 通过爬取 LinkedIn 公开页面 / 数据集获取（合规前提下）。

本爬虫用于：
* 给"技能标准化"提供权威参考
* 给"交叉验证"提供行业基准
"""
from __future__ import annotations

from typing import List, Optional

from app.core.logger import log
from app.services.crawler.base import BaseCrawler, JDItem


class OnetSpider(BaseCrawler):
    """O*NET / LinkedIn Skills 采集"""

    source_name: str = "onet"
    base_url: str = "https://www.onetonline.org"

    # O*NET 技能相关 endpoint
    SKILLS_ENDPOINT = "/find/descriptor/result/2.A.1"     # 通用技能
    KNOWLEDGE_ENDPOINT = "/find/descriptor/result/2.C"    # 知识领域
    ABILITIES_ENDPOINT = "/find/descriptor/result/2.A"    # 能力
    TOOLS_ENDPOINT = "/find/descriptor/result/2.B"        # 工具

    async def fetch(self, url: str) -> Optional[str]:
        return await self.request_with_retry(url)

    def parse(self, html: str, **kwargs) -> List[JDItem]:
        """解析 O*NET 技能/知识/能力列表"""
        items: List[JDItem] = []
        for i, node in enumerate(self.parse_html(html, ".report-td, table tr")):
            try:
                # 多种可能的结构：直接文本 / a 标签 / td
                if hasattr(node, "get_text"):
                    text = node.get_text(" ", strip=True)
                else:
                    text = str(node)
                if not text or len(text) > 200:
                    continue
                if text.lower() in {"skills", "knowledge", "abilities", "tools"}:
                    continue
                items.append(JDItem(
                    jd_id=self.make_jd_id("onet", i),
                    source=self.source_name,
                    source_url=kwargs.get("url", ""),
                    title=text,
                    category=kwargs.get("category", "技能图谱"),
                    skills=[text],
                    raw_text=text,
                ))
            except Exception as e:  # noqa: BLE001
                log.error(f"[OnetSpider] 解析第 {i} 失败: {e}")
        return items

    async def crawl(
        self,
        keyword: str = "",
        pages: int = 1,
        category: str = "技能图谱",
    ) -> List[JDItem]:
        log.info(f"[OnetSpider] keyword={keyword} pages={pages} use_mock={self.use_mock}")
        if self.use_mock:
            return self._crawl_mock(keyword, pages)

        all_items: List[JDItem] = []
        endpoints = [
            (self.SKILLS_ENDPOINT, "技能"),
            (self.KNOWLEDGE_ENDPOINT, "知识"),
            (self.ABILITIES_ENDPOINT, "能力"),
            (self.TOOLS_ENDPOINT, "工具"),
        ]
        for ep, cat in endpoints:
            url = f"{self.base_url}{ep}?keyword={keyword}"
            html = await self.fetch(url)
            if not html:
                continue
            all_items.extend(self.parse(html, url=url, category=cat))
        return self.save(all_items)


# O*NET 标准技能集（行业基准，存放在内存中供 :mod:`cleaning.onet_verifier` 引用）
ONET_STANDARD_SKILLS: List[str] = [
    # 编程语言
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust",
    "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "SQL",
    # 框架
    "React", "Angular", "Vue.js", "Node.js", "Spring", "Django", "Flask",
    "FastAPI", "Express", "TensorFlow", "PyTorch", "Keras", "Scikit-learn",
    "Hadoop", "Spark", "Flink", "Kafka",
    # 工具
    "Docker", "Kubernetes", "Git", "Jenkins", "GitLab", "Ansible", "Terraform",
    "Puppet", "Chef", "Prometheus", "Grafana", "Nginx", "Apache", "Redis",
    "Memcached", "Elasticsearch", "MongoDB", "PostgreSQL", "MySQL", "Oracle",
    "SQL Server", "Cassandra", "DynamoDB",
    # 云平台
    "AWS", "Azure", "GCP", "阿里云", "腾讯云", "华为云",
    # AI 能力
    "机器学习", "深度学习", "自然语言处理", "计算机视觉", "强化学习",
    "推荐系统", "知识图谱", "大语言模型", "检索增强生成", "Prompt Engineering",
    # 数据 / 大数据
    "数据挖掘", "数据可视化", "ETL", "数据仓库", "数据湖", "OLAP",
    "Tableau", "Power BI", "Looker", "Superset",
    # 软件工程
    "面向对象设计", "微服务", "RESTful", "GraphQL", "gRPC", "设计模式",
    "敏捷开发", "Scrum", "DevOps", "CI/CD", "测试驱动开发", "代码审查",
    # 软技能
    "团队合作", "沟通能力", "问题解决", "项目管理", "领导力",
    # 安全
    "网络安全", "渗透测试", "加密算法", "OAuth", "JWT", "SSO",
]


__all__ = ["OnetSpider", "ONET_STANDARD_SKILLS"]
