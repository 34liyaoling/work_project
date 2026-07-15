"""模拟数据生成器

因环境无法访问外网，需要为整个 pipeline 准备真实风格的"假"数据。
MockJDGenerator 可：
1. 在内存中生成指定数量的 JDItem
2. 写入 data/test_data/mock_jds.json
3. 包含"时滞"（老旧技能）、"噪声"（模糊表述）、"抄袭"（相同模板）三种典型现象
"""
from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.core.logger import log
from app.services.crawler import JDItem


# ============================================================
# 词典
# ============================================================
CITIES = ["北京", "上海", "深圳", "广州", "杭州", "成都", "南京", "武汉", "西安", "苏州", "厦门", "远程"]

COMPANIES = [
    "字节跳动", "阿里巴巴", "腾讯", "美团", "京东", "百度", "华为", "小米",
    "网易", "滴滴", "快手", "小红书", "B站", "知乎", "得物", "理想汽车",
    "蔚来", "比亚迪", "宁德时代", "蚂蚁集团", "OPPO", "vivo", "联想",
    "中兴通讯", "完美世界", "三七互娱", "米哈游", "莉莉丝", "商汤科技",
    "旷视科技", "依图科技", "云从科技", "科大讯飞", "寒武纪", "地平线",
    "深势科技", "壁仞科技", "天数智芯", "中兴", "ThoughtWorks", "Microsoft",
    "Google", "Amazon", "Meta", "Apple", "Tesla", "Netflix", "Uber",
]

LEVELS = ["初级", "中级", "高级", "资深", "专家"]

CATEGORIES = {
    "AI应用工程师": {
        "title_pool": ["AI应用工程师", "LLM应用工程师", "AI产品工程师", "Prompt工程师", "AIGC工程师"],
        "skill_pool": ["Python", "LangChain", "RAG", "检索增强生成", "向量数据库", "Milvus", "大语言模型",
                      "LLM", "提示工程", "PyTorch", "Transformers", "FastAPI", "LangChain", "AI Agent",
                      "MCP", "Embedding", "HuggingFace", "LlamaIndex", "Chroma", "FAISS"],
        "salary": (25, 60),
    },
    "Python开发工程师": {
        "title_pool": ["Python开发工程师", "Python后端开发", "Python全栈开发", "高级Python工程师"],
        "skill_pool": ["Python", "Django", "Flask", "FastAPI", "MySQL", "Redis", "MongoDB", "Docker",
                      "Kubernetes", "Linux", "Git", "RESTful", "Celery", "RabbitMQ", "Kafka",
                      "微服务", "Redis", "Nginx"],
        "salary": (15, 40),
    },
    "Java开发工程师": {
        "title_pool": ["Java开发工程师", "Java后端", "高级Java开发", "Java架构师"],
        "skill_pool": ["Java", "Spring", "Spring Boot", "MySQL", "Redis", "Kafka", "Dubbo",
                      "JVM", "多线程", "微服务", "MyBatis", "Maven", "Linux", "Docker", "Kubernetes"],
        "salary": (18, 45),
    },
    "全栈开发工程师": {
        "title_pool": ["全栈工程师", "Full Stack Engineer", "全栈开发"],
        "skill_pool": ["JavaScript", "TypeScript", "React", "Vue", "Node.js", "Python", "Java",
                      "MySQL", "MongoDB", "Redis", "Docker", "Git", "AWS", "CI/CD", "Linux"],
        "salary": (20, 50),
    },
    "数据分析师": {
        "title_pool": ["数据分析师", "业务数据分析师", "数据分析师（增长方向）", "高级数据分析师"],
        "skill_pool": ["SQL", "Python", "Pandas", "NumPy", "Excel", "Tableau", "Power BI",
                      "统计学", "A/B测试", "用户增长", "数据可视化", "ETL", "Hive"],
        "salary": (12, 35),
    },
    "数据科学家": {
        "title_pool": ["数据科学家", "高级数据科学家", "算法数据科学家", "Data Scientist"],
        "skill_pool": ["Python", "SQL", "机器学习", "深度学习", "PyTorch", "TensorFlow",
                      "统计学", "A/B测试", "Spark", "Hadoop", "Scikit-learn", "XGBoost",
                      "特征工程", "推荐系统", "自然语言处理"],
        "salary": (25, 60),
    },
    "机器学习工程师": {
        "title_pool": ["机器学习工程师", "ML Engineer", "算法工程师（机器学习）", "推荐算法工程师"],
        "skill_pool": ["Python", "机器学习", "深度学习", "PyTorch", "TensorFlow", "Scikit-learn",
                      "推荐系统", "NLP", "自然语言处理", "计算机视觉", "XGBoost", "LightGBM",
                      "Spark", "Kubernetes", "Docker", "向量数据库"],
        "salary": (28, 65),
    },
    "前端开发工程师": {
        "title_pool": ["前端工程师", "高级前端工程师", "Web前端开发", "资深前端工程师"],
        "skill_pool": ["JavaScript", "TypeScript", "React", "Vue", "Angular", "Webpack",
                      "CSS3", "HTML5", "Node.js", "Next.js", "Nuxt", "Figma", "Git", "性能优化"],
        "salary": (15, 45),
    },
    "后端开发工程师": {
        "title_pool": ["后端工程师", "服务端工程师", "高级后端开发", "Backend Engineer"],
        "skill_pool": ["Java", "Python", "Go", "MySQL", "Redis", "Kafka", "MongoDB", "Docker",
                      "Kubernetes", "微服务", "Spring Boot", "FastAPI", "Linux", "RESTful", "gRPC"],
        "salary": (18, 50),
    },
    "DevOps工程师": {
        "title_pool": ["DevOps工程师", "SRE工程师", "运维开发工程师", "云原生工程师"],
        "skill_pool": ["Linux", "Docker", "Kubernetes", "Jenkins", "GitLab CI", "GitHub Actions",
                      "AWS", "Prometheus", "Grafana", "Ansible", "Terraform", "Helm", "CI/CD",
                      "Python", "Shell", "Nginx"],
        "salary": (20, 50),
    },
    "产品经理": {
        "title_pool": ["产品经理", "高级产品经理", "AI产品经理", "增长产品经理", "B端产品经理"],
        "skill_pool": ["PRD", "Axure", "Figma", "用户调研", "数据分析", "SQL", "敏捷开发",
                      "Scrum", "需求分析", "竞品分析", "产品规划", "AI产品", "A/B测试"],
        "salary": (18, 50),
    },
    "UI设计师": {
        "title_pool": ["UI设计师", "高级UI设计师", "视觉设计师", "UI/UX设计师"],
        "skill_pool": ["Figma", "Sketch", "Photoshop", "Illustrator", "交互设计", "用户体验",
                      "设计规范", "动效设计", "C4D", "Web设计", "移动端设计", "品牌设计"],
        "salary": (12, 35),
    },
}

# 时滞（老旧技能）样本
LEGACY_SKILLS = ["jQuery", "Struts2", "Hibernate", "Spring MVC", "Tornado", "Web.py",
                 "Backbone.js", "CoffeeScript", "Sass", "Flash", "Silverlight"]

# 噪声（模糊表述）样本
NOISY_REQUIREMENTS = [
    "优秀的沟通能力", "良好的团队合作精神", "抗压能力强", "责任心强",
    "有激情", "能吃苦耐劳", "执行力强", "学习能力强", "逻辑清晰",
    "自我驱动", "对技术有热情", "拥抱变化",
]

# 抄袭模板（不同公司但用完全相同 JD 文本）
TEMPLATE_JD_TEXT = """岗位职责：
1. 负责公司核心业务系统的设计与开发
2. 参与需求评审，制定技术方案
3. 持续优化系统性能与稳定性
4. 与产品、测试紧密协作，保证项目交付质量

任职要求：
1. 本科及以上学历，计算机相关专业
2. 3年以上相关开发经验
3. 精通至少一种主流编程语言
4. 熟悉常见中间件、数据库及缓存
5. 有大型分布式系统经验者优先"""


# ============================================================
# 工具函数
# ============================================================
def _rand_salary(low: int, high: int) -> str:
    """随机生成 15K-30K·14薪 形式的薪资。"""
    a = random.randint(low, max(low, high - 5))
    b = a + random.randint(3, 15)
    months = random.choice([12, 13, 14, 15, 16])
    return f"{a}K-{b}K·{months}薪"


def _rand_date(allow_stale: bool = False) -> str:
    """随机发布时间，allow_stale=True 时 50% 概率生成 2 年前。"""
    if allow_stale and random.random() < 0.5:
        delta = timedelta(days=random.randint(730, 1500))
    else:
        delta = timedelta(days=random.randint(1, 200))
    return (datetime.now() - delta).strftime("%Y-%m-%d %H:%M:%S")


def _maybe_noisy(skills: List[str]) -> List[str]:
    """30% 概率混入 1-2 条模糊表述。"""
    if random.random() < 0.3:
        skills = list(skills) + random.sample(NOISY_REQUIREMENTS, k=random.randint(1, 2))
    return skills


# ============================================================
# MockJDGenerator
# ============================================================
class MockJDGenerator:
    """JD 模拟数据生成器。"""

    DEFAULT_OUTPUT = "./data/test_data/mock_jds.json"

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        self._template_jd_idx = 0  # 计数用于制造"抄袭"特征

    def generate(
        self,
        count: int = 100,
        category_filter: Optional[str] = None,
        source: str = "mock",
    ) -> List[JDItem]:
        """生成 count 条 JD 模拟数据。

        category_filter: 指定岗位类别，否则从全部类别中随机
        source: 数据来源标识
        """
        categories = list(CATEGORIES.keys())
        if category_filter and category_filter in CATEGORIES:
            categories = [category_filter]

        items: List[JDItem] = []
        for i in range(count):
            category = random.choice(categories)
            meta = CATEGORIES[category]
            title = random.choice(meta["title_pool"])
            company = random.choice(COMPANIES)
            level = random.choice(LEVELS)
            location = random.choice(CITIES)
            salary = _rand_salary(*meta["salary"])

            # 30% 概率注入时滞技能
            skills = random.sample(meta["skill_pool"], k=min(len(meta["skill_pool"]), random.randint(4, 8)))
            if random.random() < 0.3:
                legacy = random.choice(LEGACY_SKILLS)
                skills.append(legacy)
            skills = _maybe_noisy(skills)

            # 10% 概率生成"抄袭"模板
            is_template = random.random() < 0.1
            if is_template:
                raw_text = TEMPLATE_JD_TEXT
                self._template_jd_idx += 1
            else:
                raw_text = self._compose_raw_text(title, company, category, skills, level)

            # 20% 概率时滞（老 JD）
            published_at = _rand_date(allow_stale=random.random() < 0.2)

            jd = JDItem(
                jd_id=f"mock-{source}-{int(time.time())}-{i:05d}",
                source=source,
                source_url=f"https://example.com/{source}/{i}",
                company=company,
                title=title,
                category=category,
                level=level,
                location=location,
                salary_range=salary,
                raw_text=raw_text,
                skills=skills,
                published_at=published_at,
                extra={"is_template_copied": is_template},
            )
            items.append(jd)
        log.info(f"MockJDGenerator 生成 {len(items)} 条 JD（source={source}）")
        return items

    def _compose_raw_text(
        self,
        title: str,
        company: str,
        category: str,
        skills: List[str],
        level: str,
    ) -> str:
        """拼装真实风格的 JD 文本。"""
        skill_str = "、".join(skills)
        responsibilities = [
            f"负责{title}相关核心模块的设计、开发和维护",
            "参与系统架构设计与技术选型",
            "编写高质量代码，进行 Code Review",
            "持续优化系统性能与稳定性",
            "与产品、测试、运维紧密协作，保障项目交付",
        ]
        requirements = [
            f"{level}经验，{random.randint(1, 10)}年以上相关开发经验",
            f"熟练掌握：{skill_str}",
            "良好的代码风格与工程素养",
            "良好的沟通能力与团队协作精神",
        ]
        bonus = "有以下经验者优先："
        bonuses = random.sample(skills, k=min(3, len(skills)))

        return (
            f"# {title} - {company}\n\n"
            "## 岗位职责：\n" + "\n".join(f"{i+1}. {r}" for i, r in enumerate(responsibilities)) + "\n\n"
            "## 任职要求：\n" + "\n".join(f"{i+1}. {r}" for i, r in enumerate(requirements)) + "\n\n"
            f"## 加分项：\n{bonus}{'、'.join(bonuses)}\n"
        )

    def save_to_file(self, items: List[JDItem], path: Optional[str] = None) -> str:
        """保存到 JSON 文件。"""
        path = path or self.DEFAULT_OUTPUT
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = [it.to_dict() for it in items]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log.info(f"Mock JD 已保存到 {path}（{len(data)} 条）")
        return path

    def generate_and_save(self, count: int = 100, path: Optional[str] = None) -> str:
        """一键生成 + 保存。"""
        items = self.generate(count=count)
        return self.save_to_file(items, path)

    @staticmethod
    def load_from_file(path: str = "./data/test_data/mock_jds.json") -> List[Dict[str, Any]]:
        """从 JSON 读取 JD 列表（字典格式）。"""
        if not os.path.exists(path):
            log.warning(f"文件不存在: {path}")
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


__all__ = [
    "MockJDGenerator",
    "CATEGORIES",
    "CITIES",
    "COMPANIES",
    "LEGACY_SKILLS",
    "NOISY_REQUIREMENTS",
    "TEMPLATE_JD_TEXT",
]
