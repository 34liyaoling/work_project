"""JD智能解析器 - 用LLM从原始招聘文本中提取结构化岗位信息"""

import json
import logging
import re
import time
from typing import Optional

from core.llm_service import get_llm_service

logger = logging.getLogger(__name__)

# 解析提示词模板
JD_PARSE_PROMPT = """你是一个专业的招聘信息解析专家。请从以下原始招聘文本中提取结构化信息。

## 原始文本
{raw_text}

## 输出要求
请严格按以下JSON格式输出（不要输出其他内容）：
{{
    "job_title": "岗位名称",
    "company_name": "公司名称",
    "skills": ["技能1", "技能2", ...],  // 8-15个具体技术技能
    "salary_min": 数字或null,
    "salary_max": 数字或null,
    "location": "城市",
    "experience_min": 数字或null,
    "experience_max": 数字或null,
    "education": "学历要求",
    "domain": "人工智能|大数据|云计算|软件开发|网络安全|区块链/Web3|物联网|测试/质量",
    "description": "一句话总结该岗位的核心职责和技术栈"
}}

注意：
- skills必须是具体的技术名词（如Python、Kubernetes、PyTorch），不是泛泛的能力描述
- salary单位是K/月（如果原文是万/年请转换）
- domain根据岗位技术特征判断
- 如果某字段无法从文本中提取，使用null
"""


class JDParser:
    """JD智能解析器 - 基于LLM的招聘文本结构化提取"""

    def __init__(self):
        self.llm = None

    def _get_llm(self):
        if self.llm is None:
            self.llm = get_llm_service()
        return self.llm

    def parse_single(self, raw_text: str, source_url: str = "") -> Optional[dict]:
        """解析单条原始JD文本，返回结构化dict或None(解析失败时)"""
        try:
            llm = self._get_llm()

            # 检查LLM是否可用
            if not llm or not llm.is_ready:
                logger.warning("LLM服务不可用，使用正则表达式备用解析器")
                fallback_parser = RegexJDFallbackParser()
                return fallback_parser.parse(raw_text)

            prompt = JD_PARSE_PROMPT.format(raw_text=raw_text[:3000])  # 截断过长文本

            response = llm.chat_completion_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # 低温度保证输出稳定
            )

            if response:
                result = response
                result["source_url"] = source_url
                return result
            else:
                logger.warning(f"JD解析未返回有效结果")
                # 使用正则兜底
                fallback_parser = RegexJDFallbackParser()
                parsed = fallback_parser.parse(raw_text)
                parsed["source_url"] = source_url
                return parsed

        except Exception as e:
            logger.error(f"JD解析失败: {e}")
            # 使用正则兜底
            try:
                fallback_parser = RegexJDFallbackParser()
                parsed = fallback_parser.parse(raw_text)
                parsed["source_url"] = source_url
                return parsed
            except Exception as e2:
                logger.error(f"正则解析也失败: {e2}")
                return None

    def parse_batch(self, raw_jds: list[dict]) -> list[dict]:
        """批量解析多条原始JD，返回成功解析的结构化列表"""
        results = []
        for jd in raw_jds:
            raw_text = jd.get("raw_text", "")
            source_url = jd.get("url", "")
            parsed = self.parse_single(raw_text, source_url)
            if parsed:
                parsed["source_url"] = jd.get("url", "")
                parsed["raw_source"] = jd.get("source", "web")
                results.append(parsed)
            time.sleep(0.5)  # 避免LLM请求过快

        logger.info(f"批量JD解析完成: {len(raw_jds)} 条输入 → {len(results)} 条成功")
        return results


# 正则表达式备用解析（当LLM不可用时使用）
class RegexJDFallbackParser:
    """基于正则表达式的JD解析备选方案（无需LLM）"""

    SKILL_PATTERNS = {
        "编程语言": r"(?:熟悉|熟练|掌握|精通)\s*([A-Za-z+#]+(?:/[A-Za-z+#]+)*)",
        "框架": r"(?:Spring Boot|Django|Flask|FastAPI|Vue|React|Angular|Express|PyTorch|TensorFlow|Keras|Scikit-learn)",
        "数据库": r"(?:MySQL|PostgreSQL|MongoDB|Redis|Elasticsearch|ClickHouse|HBase|SQLite|Oracle|SQL Server)",
        "中间件": r"(?:Kafka|RabbitMQ|RocketMQ|Nacos|Consul|ZooKeeper|etcd)",
        "云原生": r"(?:Docker|Kubernetes|K8s|Istio|Helm|Terraform|Ansible|Jenkins|GitLab CI|Prometheus|Grafana)",
        "大数据": r"(?:Spark|Flink|Hadoop|Hive|HBase|Presto|Druid|Airflow|DataX|Sqoop)",
        "AI/ML": r"(?:机器学习|深度学习|神经网络|NLP|计算机视觉|推荐系统|强化学习|Transformer|BERT|GPT|LLM|RAG)",
        "安全": r"(?:渗透测试|漏洞挖掘|OWASP|逆向工程|密码学|零信任|WAF|IDS|IPS|SIEM)",
        "区块链": r"(?:Solidity|智能合约|DeFi|Web3|以太坊|区块链|IPFS|零知识证明)",
    }

    DOMAIN_KEYWORDS = {
        "人工智能": ["AI", "人工智能", "机器学习", "深度学习", "算法", "NLP", "计算机视觉", "大模型", "LLM", "PyTorch", "TensorFlow"],
        "大数据": ["大数据", "数据仓库", "ETL", "Spark", "Flink", "Hadoop", "Hive", "数据分析", "数据治理"],
        "云计算": ["云计算", "云原生", "DevOps", "SRE", "Kubernetes", "Docker", "运维", "容器"],
        "软件开发": ["开发", "工程师", "后端", "前端", "全栈", "Java", "Python", "Go", "JavaScript"],
        "网络安全": ["安全", "渗透", "漏洞", "安全工程师", "网络安全", "密码学"],
        "区块链/Web3": ["区块链", "Web3", "智能合约", "Solidity", "DeFi", "以太坊"],
        "物联网": ["物联网", "IoT", "嵌入式", "边缘计算", "传感器", "MQTT"],
        "测试/质量": ["测试", "QA", "质量", "自动化测试", "性能测试"],
    }

    def parse(self, raw_text: str) -> dict:
        """用正则从JD文本中提取基本信息"""
        result = {
            "job_title": "",
            "company_name": "",
            "skills": [],
            "salary_min": None,
            "salary_max": None,
            "location": "",
            "experience_min": None,
            "experience_max": None,
            "education": "",
            "domain": "软件开发",
            "description": "",
        }

        # 提取技能
        for category, pattern in self.SKILL_PATTERNS.items():
            matches = re.findall(pattern, raw_text, re.IGNORECASE)
            for m in matches:
                skill = m if isinstance(m, str) else m[0]
                if skill and len(skill) > 1 and len(skill) < 50:
                    result["skills"].append(skill)

        # 去重
        result["skills"] = list(set(result["skills"]))[:15]  # 最多保留15个

        # 提取薪资
        salary_patterns = [
            r'(\d+)k?\s*[-~至]\s*(\d+)k?',  # 20k-30k
            r'(\d+)\s*-\s*(\d+)\s*[万千]',   # 20-30万
            r'薪资[:：]\s*(\d+)[万千]?',      # 薪资30万
        ]
        for pat in salary_patterns:
            m = re.search(pat, raw_text, re.IGNORECASE)
            if m:
                result["salary_min"] = int(m.group(1))
                result["salary_max"] = int(m.group(2))
                break

        # 提取经验
        exp_m = re.search(r'(\d+)[-~至](\d+)\s*年', raw_text)
        if exp_m:
            result["experience_min"] = int(exp_m.group(1))
            result["experience_max"] = int(exp_m.group(2))

        # 提取学历
        edu_patterns = [
            (r'(博士)', '博士'),
            (r'(硕士|研究生)', '硕士'),
            (r'(本科)', '本科'),
            (r'(大专|专科)', '大专'),
        ]
        for pat, level in edu_patterns:
            if re.search(pat, raw_text):
                result["education"] = level
                break

        # 提取城市
        city_pattern = r'(北京|上海|广州|深圳|杭州|成都|南京|武汉|西安|重庆|天津|苏州|长沙|郑州|东莞|青岛|沈阳|宁波|昆明)'
        city_m = re.search(city_pattern, raw_text)
        if city_m:
            result["location"] = city_m.group(1)

        # 判断领域
        max_match_count = 0
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            match_count = sum(1 for kw in keywords if kw.lower() in raw_text.lower())
            if match_count > max_match_count:
                max_match_count = match_count
                result["domain"] = domain

        # 提取描述（取前200字作为描述）
        clean_text = re.sub(r'\s+', ' ', raw_text).strip()
        result["description"] = clean_text[:200]

        return result
