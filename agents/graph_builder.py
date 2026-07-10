import logging
from typing import Any
from .base_agent import BaseKnowledgeAgent
from core.graph_service import get_graph_service
from core.llm_service import get_llm_service
from core.vector_service import get_vector_service
from models.graph_nodes import LifecycleStage, JobStatus
from models.job_model import JobPostSource

logger = logging.getLogger(__name__)


class GraphBuilderAgent(BaseKnowledgeAgent):
    agent_name = "graph_builder"
    agent_description = "图谱构建Agent - 负责构建技能知识图谱"

    def __init__(self):
        super().__init__()
        self.graph = get_graph_service()
        self.vector_service = get_vector_service()
        self.normalizer = None
        self.inferrer = None
        self.logger = logger

    def _setup_tools(self):
        pass

    def _form_hypothesis(self, task_input, perception):
        action = task_input.get("action", "init_graph")
        return {"action": action}

    def _act(self, hypothesis, task_input, **kwargs):
        action = hypothesis["action"]
        if action == "seed_graph":
            result = self.init_knowledge_graph()
        elif action == "build_from_data":
            data = task_input.get("data", [])
            result = self.build_from_data(data)
        elif action == "init_graph":
            result = self.init_knowledge_graph()
        else:
            result = {"success": False, "error": f"Unknown action: {action}"}
        return result

    def _infer_category(self, skill_name: str) -> str:
        """根据技能名称推断所属分类"""
        known_categories = {
            "编程语言": ["Python", "Java", "Go", "Rust", "C++", "C#", "TypeScript", "JavaScript",
                       "Kotlin", "Swift", "Scala", "Ruby", "Shell", "SQL"],
            "深度学习框架": ["PyTorch", "TensorFlow", "Keras", "MXNet", "PaddlePaddle", "JAX",
                         "Caffe", "Theano"],
            "大模型技术": ["Transformer", "BERT", "GPT", "LLM", "RAG", "LangChain",
                        "Fine-tuning", "Prompt Engineering", "LoRA", "模型蒸馏", "vLLM"],
            "容器与编排": ["Docker", "Kubernetes", "Swarm", "Mesos", "Containerd", "Podman"],
            "数据库": ["MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch", "ClickHouse",
                     "HBase", "Cassandra", "DynamoDB", "TIDB", "StarRocks", "Doris"],
            "数据处理": ["Spark", "Flink", "Hadoop", "Hive", "Kafka", "Storm", "Presto",
                       "Airflow", "ETL", "Data Pipeline"],
            "架构设计": ["微服务架构", "分布式系统", "高并发", "高可用设计", "DDD",
                       "事件驱动架构", "CQRS", "Serverless", "云原生架构"],
            "DevOps": ["CI/CD", "Jenkins", "GitLab CI", "GitHub Actions", "Ansible",
                      "Terraform", "Prometheus", "Grafana", "ELK"],
            "前端": ["React", "Vue", "Angular", "Webpack", "Vite", "TypeScript", "CSS",
                    "HTML", "Node.js", "Next.js", "Nuxt"],
            "安全": ["网络安全", "渗透测试", "漏洞挖掘", "安全审计", "密码学",
                    "身份认证", "OWASP", "零信任"],
        }
        skill_lower = skill_name.lower()
        for category, skills in known_categories.items():
            if any(s.lower() == skill_lower for s in skills):
                return category
        for category, skills in known_categories.items():
            if any(s.lower() in skill_lower for s in skills):
                return category
        return "其他技术"

    def build_from_data(self, data: list[dict]) -> dict:
        """根据采集数据构建图谱节点和关系（集成标准化+关系推断+质量校验）"""
        if not data:
            logger.warning("build_from_data: 没有提供数据，跳过构建")
            return {"jobs_updated": 0, "skills_added": 0}

        if not self.graph.is_connected:
            self.graph.connect()

        if not self.graph.is_connected:
            return {"jobs_updated": 0, "skills_added": 0, "error": "Neo4j未连接"}

        # 延迟加载标准化器和推断器
        if self.normalizer is None:
            from core.entity_normalizer import EntityNormalizer
            self.normalizer = EntityNormalizer()
        if self.inferrer is None:
            from core.relation_inferrer import RelationInferrer
            self.inferrer = RelationInferrer(self.graph)

        jobs_updated = 0
        skills_added = 0
        seen_skills = set()
        all_processed_skills = []

        for item in data:
            job_title = item.get("job_title", item.get("title", ""))
            if not job_title:
                continue

            source = item.get("source", "web_search")

            job_data = {
                "title": job_title,
                "domain": item.get("domain", self._infer_domain(job_title)),
                "salary_min": item.get("salary_min"),
                "salary_max": item.get("salary_max"),
                "experience_min": item.get("experience_min"),
                "experience_max": item.get("experience_max"),
                "location": item.get("location"),
                "company_size": item.get("company_size"),
                "industry": item.get("industry"),
                "description": item.get("description", ""),
                "source": source,
                "source_url": item.get("source_url", ""),
            }

            self.graph.create_job_node(job_data)
            jobs_updated += 1

            for skill_name in item.get("skills", []):
                if not skill_name or not str(skill_name).strip():
                    continue

                # 第1步：标准化技能名称
                normalized = self.normalizer.normalize(skill_name)
                if not normalized:
                    continue

                if normalized not in seen_skills:
                    seen_skills.add(normalized)
                    all_processed_skills.append(normalized)

                # 第2步：创建技能节点
                skill_data = {
                    "name": normalized,
                    "category": self._infer_category(normalized),
                    "domain": item.get("domain", self._infer_domain(job_title)),
                }
                self.graph.create_skill_node(skill_data)
                skills_added += 1

                # 第3步：创建岗位-技能关系
                self.graph.create_requires_relation(job_title, normalized)

        # 第4步：执行关系推断
        logger.info("标准化完成，开始关系推断...")
        infer_result = self.inferrer.infer_all(
            all_skills=list(seen_skills)
        )

        # 第5步：质量校验（幻觉防控 L2）
        try:
            from core.hallucination_guard import get_hallucination_guard
            guard = get_hallucination_guard()
            if guard:
                constraint_errors = guard.constraint_engine.check_all()
                if constraint_errors:
                    logger.warning(f"图谱质量校验发现 {len(constraint_errors)} 个问题")
        except Exception as e:
            logger.warning(f"质量校验失败: {e}")

        # 第6步：质量守护Agent主动检查（数据质量+图谱质量+合规）
        quality_report = None
        try:
            from agents.quality_guardian import QualityGuardianAgent
            guardian = QualityGuardianAgent()
            quality_report = guardian.run_full_check()
            issues = quality_report.get("issues_found", 0)
            status = quality_report.get("overall_status", "unknown")
            logger.info(f"质量守护检查完成: 状态={status}, 发现{issues}个问题")
            if issues > 0:
                for category, detail in quality_report.items():
                    if isinstance(detail, dict) and detail.get("issues"):
                        for issue in detail["issues"]:
                            logger.warning(f"  质量问题[{category}]: {issue}")
        except Exception as e:
            logger.warning(f"质量守护Agent执行失败: {e}")

        logger.info(f"图谱构建完成: 新增 {jobs_updated} 个岗位, "
                    f"{skills_added} 个技能关系, "
                    f"推断 {infer_result.get('total_relations', 0)} 个关系")
        return {
            "jobs_updated": jobs_updated,
            "skills_added": skills_added,
            "inferred_relations": infer_result,
            "quality_report": quality_report,
        }

    def _infer_domain(self, job_title: str) -> str:
        """根据岗位名称推断所属领域"""
        title_lower = job_title.lower()
        domain_keywords = {
            "人工智能": ["ai", "人工智能", "算法", "机器学习", "深度学习", "nlp", "自然语言",
                       "计算机视觉", "大模型", "llm", "推荐", "搜索算法", "语音"],
            "大数据": ["大数据", "数据仓库", "数据开发", "实时计算", "flink", "spark",
                     "数据治理", "数据分析", "数据科学"],
            "云计算": ["云原生", "云架构", "devops", "sre", "运维开发", "k8s",
                     "kubernetes", "docker", "平台架构"],
            "软件开发": ["开发", "后端", "前端", "全栈", "架构师", "java", "python",
                       "go", "rust", "c++", "测试开发", "移动端", "ios", "android"],
            "网络安全": ["安全", "网络", "渗透", "漏洞", "合规", "风控"],
            "区块链": ["区块链", "web3", "solidity", "智能合约", "nft"],
            "物联网": ["iot", "物联网", "嵌入式", "边缘计算"],
        }
        for domain, keywords in domain_keywords.items():
            if any(kw in title_lower for kw in keywords):
                return domain
        return "软件开发"

    def get_graph_stats(self) -> dict:
        return self.graph.get_graph_stats()

    def init_knowledge_graph(self) -> dict:
        """初始化知识图谱Schema和基础分类"""
        if not self.graph.is_connected:
            self.graph.connect()
        if self.graph.is_connected:
            self.graph.initialize_schema()
        return {
            "graph_initialized": self.graph.is_connected,
            "jobs_updated": 0,
            "skills_added": 0,
        }

    def initialize_full_graph(self) -> dict:
        """完整初始化：创建Schema，不从种子数据写入"""
        return self.init_knowledge_graph()
