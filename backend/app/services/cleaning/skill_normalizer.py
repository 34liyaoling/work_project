"""技能标准化映射

把各种各样的别名 / 缩写 / 拼写变体映射到"标准技能名"。

数据源：
* :data:`data/skill_dictionary.json`  （200+ 技能）
* 内置常用别名补充

提供：
* :class:`SkillNormalizer` - 标准化器
* :func:`normalize_skill` - 单条技能标准化
* :func:`normalize_skills` - 技能列表标准化（去重 + 排序）
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

from app.core.config import settings
from app.core.logger import log


# ============================================================
# 内置补充别名（覆盖 json 文件外的常见变体）
# ============================================================
_BUILTIN_ALIASES: Dict[str, Tuple[str, str]] = {
    # 编程语言
    "py": ("Python", "编程语言"),
    "python3": ("Python", "编程语言"),
    "java8": ("Java", "编程语言"),
    "java11": ("Java", "编程语言"),
    "java17": ("Java", "编程语言"),
    "golang": ("Go", "编程语言"),
    "go-lang": ("Go", "编程语言"),
    "cpp": ("C++", "编程语言"),
    "c plus plus": ("C++", "编程语言"),
    "c#": ("C#", "编程语言"),
    "csharp": ("C#", "编程语言"),
    "node": ("Node.js", "运行时"),
    "nodejs": ("Node.js", "运行时"),
    "expressjs": ("Express.js", "Web框架"),
    "express.js": ("Express.js", "Web框架"),
    "reactjs": ("React", "Web框架"),
    "react.js": ("React", "Web框架"),
    "vuejs": ("Vue", "Web框架"),
    "vue.js": ("Vue.js", "Web框架"),
    "vue2": ("Vue.js", "Web框架"),
    "vue3": ("Vue.js", "Web框架"),
    "ng": ("Angular", "Web框架"),
    "angularjs": ("Angular", "Web框架"),
    "next": ("Next.js", "Web框架"),
    "nextjs": ("Next.js", "Web框架"),
    "nuxtjs": ("Nuxt.js", "Web框架"),
    # AI / 数据
    "机器学习算法": ("机器学习", "AI"),
    "深度神经网络": ("深度学习", "AI"),
    "cv": ("计算机视觉", "AI"),
    "nlp": ("自然语言处理", "AI"),
    "llm大模型": ("大语言模型", "AI"),
    "gpt": ("大语言模型", "AI"),
    "chatgpt": ("大语言模型", "AI"),
    "rag": ("检索增强生成", "AI"),
    "transformer": ("Transformers", "AI框架"),
    "huggingface": ("HuggingFace", "AI框架"),
    "hf": ("HuggingFace", "AI框架"),
    "sklearn": ("Scikit-learn", "机器学习框架"),
    "scikit learn": ("Scikit-learn", "机器学习框架"),
    "tf": ("TensorFlow", "深度学习框架"),
    "torch": ("PyTorch", "深度学习框架"),
    "xgb": ("XGBoost", "机器学习框架"),
    "lgbm": ("LightGBM", "机器学习框架"),
    "lightgbm": ("LightGBM", "机器学习框架"),
    "milvus": ("Milvus", "向量数据库"),
    "chromadb": ("Chroma", "向量数据库"),
    "向量检索": ("向量数据库", "AI基础设施"),
    "embeddings": ("Embedding", "AI"),
    "embedding model": ("Embedding", "AI"),
    # 大数据
    "hdfs": ("HDFS", "大数据"),
    "hive sql": ("Hive", "大数据"),
    "spark sql": ("Spark", "大数据"),
    "pyspark": ("Spark", "大数据"),
    "kafka streaming": ("Kafka", "消息队列"),
    "rabbitmq": ("RabbitMQ", "消息队列"),
    "rocketmq": ("RocketMQ", "消息队列"),
    "elastic": ("Elasticsearch", "搜索引擎"),
    "es": ("Elasticsearch", "搜索引擎"),
    "clickhouse": ("ClickHouse", "数据库"),
    "ck": ("ClickHouse", "数据库"),
    "pg": ("PostgreSQL", "数据库"),
    "postgres": ("PostgreSQL", "数据库"),
    "mongo": ("MongoDB", "数据库"),
    "redis cluster": ("Redis", "数据库"),
    "mssql": ("SQL Server", "数据库"),
    # DevOps / 云
    "k8s": ("Kubernetes", "容器编排"),
    "kuber": ("Kubernetes", "容器编排"),
    "kubernetes(k8s)": ("Kubernetes", "容器编排"),
    "docker compose": ("Docker Compose", "容器"),
    "dockerfile": ("Docker", "容器"),
    "helm chart": ("Helm", "容器编排"),
    "aliyun": ("阿里云", "云服务"),
    "amazon web services": ("AWS", "云服务"),
    "amazon aws": ("AWS", "云服务"),
    "google cloud": ("GCP", "云服务"),
    "azure cloud": ("Azure", "云服务"),
    "ci/cd pipeline": ("CI/CD", "工程实践"),
    "cicd": ("CI/CD", "工程实践"),
    "git ops": ("GitOps", "工程实践"),
    # 测试
    "selenium webdriver": ("Selenium", "测试"),
    "pytest": ("Pytest", "测试"),
    "junit": ("JUnit", "测试"),
    "testng": ("TestNG", "测试"),
    "jmeter": ("JMeter", "测试"),
    "postman test": ("Postman", "测试"),
    # 设计
    "ps": ("Photoshop", "设计工具"),
    "ai design": ("Illustrator", "设计工具"),
    "fig": ("Figma", "设计工具"),
    "sketch app": ("Sketch", "设计工具"),
    # 软技能 / 项目管理
    "tdd": ("测试驱动开发", "工程实践"),
    "ddd": ("领域驱动设计", "工程实践"),
    "okr": ("OKR", "管理"),
    "agile": ("敏捷开发", "工程实践"),
    "scrum master": ("Scrum", "工程实践"),
    "pm": ("项目管理", "管理"),
}


# ============================================================
# Normalizer
# ============================================================
@dataclass
class SkillNormalizer:
    """技能标准化器

    Attributes:
        dict_path: 技能词典 JSON 路径
        alias_index: 别名 → (标准名, 分类) 索引
        standard_set: 所有标准技能集合
    """

    dict_path: str = field(default_factory=lambda: settings.SKILL_DICT_PATH)
    alias_index: Dict[str, Tuple[str, str]] = field(default_factory=dict)
    standard_set: Set[str] = field(default_factory=set)
    category_index: Dict[str, str] = field(default_factory=dict)  # 标准名 -> 分类

    def __post_init__(self) -> None:
        self._load_dict()
        self._merge_builtin()

    # -------------------------------------------------------- 加载
    def _load_dict(self) -> None:
        if not os.path.exists(self.dict_path):
            log.warning(f"技能词典不存在: {self.dict_path}")
            return
        try:
            with open(self.dict_path, "r", encoding="utf-8") as f:
                rows = json.load(f)
            for row in rows:
                alias = (row.get("alias") or "").strip()
                std = (row.get("standard_name") or "").strip()
                cat = (row.get("category") or "").strip() or "未分类"
                if not alias or not std:
                    continue
                self.alias_index[alias.lower()] = (std, cat)
                self.standard_set.add(std)
                # 同一标准名只保留第一个分类
                self.category_index.setdefault(std, cat)
            log.info(f"技能词典加载完成: {len(self.alias_index)} 条别名，{len(self.standard_set)} 个标准名")
        except Exception as e:  # noqa: BLE001
            log.error(f"技能词典加载失败: {e}")

    def _merge_builtin(self) -> None:
        """合并内置补充别名"""
        added = 0
        for k, (std, cat) in _BUILTIN_ALIASES.items():
            if k.lower() not in self.alias_index:
                self.alias_index[k.lower()] = (std, cat)
                self.standard_set.add(std)
                self.category_index.setdefault(std, cat)
                added += 1
        if added:
            log.info(f"合并内置别名: {added} 条")

    # -------------------------------------------------------- 标准化
    def normalize(self, skill: str) -> Tuple[str, str]:
        """单条技能 → (标准名, 分类)"""
        if not skill:
            return ("", "")
        key = skill.strip().lower()
        if key in self.alias_index:
            return self.alias_index[key]
        # 模糊回退：去空格 / 去括号
        key2 = re.sub(r"[\s()（）·/／,，、]+", "", key)
        for k, v in self.alias_index.items():
            k2 = re.sub(r"[\s()（）·/／,，、]+", "", k)
            if k2 == key2:
                return v
        # 没有命中：原样作为新标准
        return (skill.strip(), "未分类")

    def normalize_list(self, skills: Iterable[str]) -> List[Dict[str, str]]:
        """批量标准化：返回 ``[{"skill": 标准名, "category": 分类, "original": 原值}]``

        同时去重（按标准名）。
        """
        seen: Set[str] = set()
        out: List[Dict[str, str]] = []
        for s in skills or []:
            std, cat = self.normalize(s)
            if not std:
                continue
            if std in seen:
                continue
            seen.add(std)
            out.append({"skill": std, "category": cat, "original": s})
        return out

    def is_standard(self, skill: str) -> bool:
        """判断是否已经为标准名"""
        return skill in self.standard_set

    def get_category(self, standard_skill: str) -> str:
        return self.category_index.get(standard_skill, "未分类")


# ============================================================
# 模块级单例 + 便捷函数
# ============================================================
_default_normalizer: Optional[SkillNormalizer] = None


def get_normalizer() -> SkillNormalizer:
    """获取默认标准化器（单例）"""
    global _default_normalizer
    if _default_normalizer is None:
        _default_normalizer = SkillNormalizer()
    return _default_normalizer


def normalize_skill(skill: str) -> str:
    """单条技能标准化（仅返回标准名）"""
    return get_normalizer().normalize(skill)[0]


def normalize_skills(skills: Iterable[str]) -> List[str]:
    """批量标准化（去重，返回字符串列表）"""
    return [it["skill"] for it in get_normalizer().normalize_list(skills)]


__all__ = [
    "SkillNormalizer",
    "get_normalizer",
    "normalize_skill",
    "normalize_skills",
]
