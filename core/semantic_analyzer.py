"""语义分析器 - 超越关键词匹配的深层语义理解"""

import logging
from typing import Optional
from core.llm_service import get_llm_service

logger = logging.getLogger(__name__)


# 隐含技能推理规则库
IMPLICIT_SKILL_RULES = {
    # 高并发相关
    "高并发": {
        "inferred_skills": ["Redis", "Kafka", "RabbitMQ", "负载均衡(Nginx)",
                          "分布式锁", "连接池", "缓存策略"],
        "confidence": 0.75,
        "category": "architecture"
    },
    "亿级流量": {
        "inferred_skills": ["分库分表", "CDN", "读写分离", "消息队列",
                          "微服务拆分", "弹性伸缩"],
        "confidence": 0.80,
        "category": "scale"
    },
    "海量数据": {
        "inferred_skills": ["Hadoop", "Spark", "Hive", "数据湖", "ETL",
                          "数据管道", "批处理"],
        "confidence": 0.75,
        "category": "bigdata"
    },
    # 微服务相关
    "微服务": {
        "inferred_skills": ["Docker", "Kubernetes", "Spring Cloud", "服务网关",
                          "配置中心", "服务发现", "链路追踪"],
        "confidence": 0.85,
        "category": "microservice"
    },
    "分布式": {
        "inferred_skills": ["RPC", "分布式事务", "CAP理论", "一致性算法",
                          "分布式缓存", "消息中间件"],
        "confidence": 0.75,
        "category": "distributed"
    },
    # AI/ML相关
    "大模型": {
        "inferred_skills": ["LangChain", "LlamaIndex", "Prompt Engineering",
                          "RAG系统设计", "API调用", "Token管理"],
        "confidence": 0.85,
        "category": "ai_llm"
    },
    "机器学习": {
        "inferred_skills": ["Python", "NumPy", "Pandas", "Scikit-learn",
                          "特征工程", "模型训练", "模型评估"],
        "confidence": 0.80,
        "category": "ml"
    },
    "深度学习": {
        "inferred_skills": ["PyTorch/TensorFlow", "CUDA", "GPU编程", "模型优化",
                          "神经网络", "反向传播"],
        "confidence": 0.80,
        "category": "dl"
    },
    "NLP": {
        "inferred_skills": ["分词", "命名实体识别", "文本分类", "Transformer",
                          "BERT", "Word2Vec", "预训练模型"],
        "confidence": 0.80,
        "category": "nlp"
    },
    "CV/计算机视觉": {
        "inferred_skills": ["CNN", "OpenCV", "YOLO", "图像分割", "目标检测",
                          "图像预处理", "数据增强"],
        "confidence": 0.80,
        "category": "cv"
    },
    "推荐系统": {
        "inferred_skills": ["协同过滤", "矩阵分解", "深度推荐", "召回/排序",
                          "特征交叉", "A/B测试"],
        "confidence": 0.75,
        "category": "recommendation"
    },
    # 数据相关
    "数据分析": {
        "inferred_skills": ["SQL", "Excel/Tableau", "数据可视化", "统计分析",
                          "Pandas", "报表开发"],
        "confidence": 0.80,
        "category": "data_analysis"
    },
    "数据仓库": {
        "inferred_skills": ["Hive", "Spark SQL", "数仓建模", "维度建模",
                          "ETL/ELT", "数据治理"],
        "confidence": 0.80,
        "category": "data_warehouse"
    },
    # 安全相关
    "安全": {
        "inferred_skills": ["HTTPS/TLS", "OAuth2/JWT", "XSS/CSRF防护", "SQL注入防护",
                          "加密算法", "权限控制", "审计日志"],
        "confidence": 0.70,
        "category": "security"
    },
    # 前端相关
    "前端性能优化": {
        "inferred_skills": ["Webpack/Vite", "懒加载", "CDN", "浏览器缓存",
                          "性能监控", "Core Web Vitals"],
        "confidence": 0.75,
        "category": "frontend_perf"
    },
    # 运维相关
    "CI/CD": {
        "inferred_skills": ["Jenkins", "GitHub Actions", "GitLab CI", "Docker",
                          "自动化部署", "流水线"],
        "confidence": 0.85,
        "category": "cicd"
    },
    "监控告警": {
        "inferred_skills": ["Prometheus", "Grafana", "ELK Stack", "日志收集",
                          "指标采集", "告警规则"],
        "confidence": 0.80,
        "category": "monitoring"
    },
}


class SemanticAnalyzer:
    """深度语义分析器

    能力：
    1. 隐含技能推断 - 从项目描述中推断未明确提及的技能
    2. 项目复杂度评估 - 评估项目的技术复杂度
    3. 文本语义理解 - 理解自然语言中的技术含义
    4. Red Flag检测 - 识别夸大或模糊描述
    """

    def __init__(self):
        self.llm = get_llm_service()
        self.rules = IMPLICIT_SKILL_RULES

    def infer_implicit_skills(self, text: str, explicit_skills: list[str] = None) -> list[dict]:
        """从文本中推断隐含技能

        Args:
            text: 待分析的文本（如项目描述、工作经历）
            explicit_skills: 已知的显式技能列表（避免重复）

        Returns:
            推断出的隐含技能列表: [{"skill": str, "confidence": float, "evidence": str, "rule": str}]
        """
        explicit_skills = explicit_skills or set()
        inferred = []

        # 基于规则的快速推断
        for keyword, rule_info in self.rules.items():
            if keyword.lower() in text.lower():
                for skill in rule_info["inferred_skills"]:
                    # 提取技能名（去掉括号内的说明）
                    skill_name = skill.split("(")[0].strip()

                    # 不重复推断已有技能
                    if skill_name.lower() not in {s.lower() for s in explicit_skills}:
                        if skill_name.lower() not in {i["skill"].lower() for i in inferred}:
                            inferred.append({
                                "skill": skill_name,
                                "confidence": rule_info["confidence"],
                                "evidence": f"文本包含关键词'{keyword}'",
                                "rule": keyword,
                                "category": rule_info.get("category", "unknown"),
                            })

        # 基于LLM的深度推断（当规则覆盖不足时）
        if len(inferred) < 3 and len(text) > 100:
            llm_inferred = self._llm_infer(text, explicit_skills)
            for item in llm_inferred:
                skill_name = item.get("skill", "")
                if skill_name and skill_name.lower() not in {i["skill"].lower() for i in inferred}:
                    if skill_name.lower() not in {s.lower() for s in explicit_skills}:
                        inferred.append(item)

        # 按置信度排序
        inferred.sort(key=lambda x: x["confidence"], reverse=True)
        return inferred

    def evaluate_project_complexity(self, project_description: str,
                                     technologies: list[str] = None) -> dict:
        """评估项目复杂度

        Args:
            project_description: 项目描述文本
            technologies: 使用的技术栈

        Returns:
            复杂度评估结果
        """
        techs = technologies or []
        text = project_description.lower()

        complexity_indicators = {
            # 高复杂度指标 (+2~3分)
            "distributed_system": ["分布式", "微服务", "集群", "高并发", "亿级", "海量",
                                   "大规模", "多机房", "异地多活", "容灾"],
            "ai_ml": ["深度学习", "神经网络", "大模型", "训练", "推理", "模型优化",
                    "强化学习", "GAN", "Diffusion", "Transformer"],
            "advanced_architecture": ["事件驱动", "CQRS", "DDD", "领域驱动", "六边形架构",
                                    "Clean Architecture", "Serverless"],
            "high_scale": ["百万级", "千万级", "亿级TPS", "PB级", "万级QPS"],

            # 中等复杂度指标 (+1分)
            "database_complex": ["分库分表", "读写分离", "索引优化", "慢查询优化",
                               "主从复制", "Sharding"],
            "cache_system": ["Redis", "Memcached", "多级缓存", "缓存穿透", "缓存雪崩"],
            "queue_system": ["Kafka", "RabbitMQ", "RocketMQ", "消息队列", "异步处理"],
            "container_orchestration": ["Kubernetes", "K8s", "Helm", "Istio", "服务网格"],

            # 低复杂度指标 (基准)
            "basic_crud": ["增删改查", "CRUD", "基础功能", "简单的", "基本"],
        }

        score = 3.0  # 基准分（CRUD型项目）
        detected_indicators = []

        for category, keywords in complexity_indicators.items():
            for kw in keywords:
                if kw in text or kw.lower() in text.lower():
                    if category in ("distributed_system", "ai_ml", "advanced_architecture", "high_scale"):
                        score += 2.5
                    elif category in ("database_complex", "cache_system",
                                      "queue_system", "container_orchestration"):
                        score += 1.5
                    detected_indicators.append({"keyword": kw, "category": category})

        # 技术栈加分
        advanced_techs = {"Kubernetes", "Spark", "TensorFlow", "PyTorch", "Flink",
                         "RabbitMQ", "Kafka", "Elasticsearch", "Dubbo"}
        for t in techs:
            if t in advanced_techs:
                score += 0.5

        # 归一化到0-10
        normalized_score = min(max(score, 1), 10)

        # 确定复杂度等级
        if normalized_score >= 7:
            level = "very_high"
        elif normalized_score >= 5:
            level = "high"
        elif normalized_score >= 3.5:
            level = "medium"
        else:
            level = "low"

        return {
            "score": round(normalized_score, 1),
            "level": level,
            "max_possible": 10,
            "detected_indicators": detected_indicators,
            "tech_count": len(techs),
        }

    def detect_red_flags(self, text: str) -> list[dict]:
        """检测Red Flag（夸大/模糊/可疑描述）"""
        red_flags = []

        # 模糊量词
        vague_terms = [
            ("大量", "使用了模糊量词'大量'，缺乏具体数字"),
            ("很多", "使用了模糊量词'很多'，缺乏具体数字"),
            ("非常熟悉", "声称'非常熟悉'但缺少具体证明"),
            ("精通", "声称'精通'但缺少项目细节支撑"),
            ("精通各种", "'精通各种'过于宽泛，无法判断真实水平"),
            ("负责...等重要工作", "笼统描述，未说明具体贡献"),
            ("参与...的设计", "'参与'不等于主导，实际深度未知"),
            ("主导了", "声称'主导'需有更多细节佐证"),
        ]

        for term, reason in vague_terms:
            if term in text:
                red_flags.append({
                    "type": "vague_language",
                    "term": term,
                    "severity": "medium",
                    "reason": reason,
                })

        # 技术栈堆砌检测（罗列过多技术但无细节）
        tech_stack_pattern = re.compile(
            r'(?:熟悉|掌握|了解|使用过)\s*([\u4e00-\u9fa5\w]+(?:、|,|\s*){5,})'
        )
        matches = tech_stack_pattern.findall(text)
        for match in matches:
            tech_list = [t.strip() for t in re.split(r'[、,]', match) if t.strip()]
            if len(tech_list) >= 8:
                red_flags.append({
                    "type": "tech_stack_stuffing",
                    "severity": "low",
                    "reason": f"一次性罗列{len(tech_list)}项技术，可能存在堆砌嫌疑",
                    "technologies": tech_list,
                })

        # 时间线矛盾检测（简单版）
        date_patterns = re.findall(r'(20\d{2})', text)
        if len(date_patterns) >= 2:
            years = sorted(set(int(d) for d in date_patterns))
            if years[-1] - years[0] > 15:
                red_flags.append({
                    "type": "timeline_concern",
                    "severity": "low",
                    "reason": f"时间跨度{years[-1]-years[0]}年较长，请注意核实",
                })

        return red_flags

    def analyze_text_semantics(self, text: str) -> dict:
        """全面的文本语义分析"""
        implicit_skills = self.infer_implicit_skills(text)
        complexity = self.evaluate_project_complexity(text)
        red_flags = self.detect_red_flags(text)

        return {
            "implicit_skills": implicit_skills,
            "complexity": complexity,
            "red_flags": red_flags,
            "text_length": len(text),
            "analysis_timestamp": __import__('datetime').datetime.now().isoformat(),
        }

    def _llm_infer(self, text: str, explicit_skills: set) -> list[dict]:
        """使用LLM进行隐含技能推断（备选方案）"""
        prompt = f"""你是一个技术能力分析专家。请从以下项目/工作描述中，推断出未明确提及但可以合理推断出候选人具备的技术技能。

已知已明确的技能: {', '.join(explicit_skills) if explicit_skills else '无'}

待分析文本:
{text}

请以JSON数组格式输出，每项包含:
- skill: 推断的技能名称
- confidence: 置信度(0.0-1.0)
- evidence: 推断理由

只输出JSON数组，不要其他内容。"""

        try:
            result = self.llm.structured_extraction(
                text=text,
                extraction_schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "skill": {"type": "string"},
                            "confidence": {"type": "number"},
                            "evidence": {"type": "string"},
                        }
                    }
                },
                system_prompt="你是技术能力分析专家，擅长从项目描述中推断隐含技术技能。"
            )

            if isinstance(result, dict) and "items" in result:
                return result.get("items", [])
            elif isinstance(result, list):
                return result
        except Exception as e:
            logger.debug(f"LLM隐含技能推断失败: {e}")

        return []


import re
