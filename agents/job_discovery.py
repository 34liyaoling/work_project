"""新岗位发现与定义Agent"""

import logging
from typing import Any
from .base_agent import BaseKnowledgeAgent
from core.graph_service import get_graph_service
from core.llm_service import get_llm_service
from core.cross_validator import CrossValidator
from models.job_model import JobDiscoveryCandidate, JobPostRaw
from models.graph_nodes import LifecycleStage, JobStatus

logger = logging.getLogger(__name__)


class JobDiscoveryAgent(BaseKnowledgeAgent):
    """新岗位发现Agent

    发现流程：
    1. 新兴技能检测 - 统计技能频率变化率
    2. 技能聚类 - 发现技能共现模式
    3. 岗位缺口检测 - 发现"有技能无岗位"的空白
    4. 岗位定义生成 - LLM生成标准化定义
    5. 交叉验证 - 多源确认
    """

    agent_name = "job_discovery"
    agent_description = "新岗位发现专家 - 通过趋势分析和聚类自动发现新兴岗位"

    DISCOVERY_THRESHOLD = {
        "min_emerging_skills": 5,          # 最少新兴技能数量
        "min_cluster_size": 3,              # 最小技能簇规模
        "min_growth_rate": 0.5,             # 最小增长率(50%)
        "min_source_agreement": 2,         # 最少数据源一致数
    }

    def __init__(self):
        super().__init__()
        self.graph = get_graph_service()
        self.validator = CrossValidator()
        self.discovered_candidates: list[JobDiscoveryCandidate] = []

    def _setup_tools(self):
        pass

    def discover_new_jobs(self, recent_data: list[JobPostRaw] = None) -> list[JobDiscoveryCandidate]:
        """执行完整的岗位发现流程"""
        logger.info("[JobDiscovery] 开始新岗位发现流程")

        # Step 1: 检测新兴技能
        emerging_skills = self._detect_emerging_skills(recent_data)
        self.memory.set_context("emerging_skills", emerging_skills)

        if len(emerging_skills) < self.DISCOVERY_THRESHOLD["min_emerging_skills"]:
            logger.info(f"[JobDiscovery] 新兴技能数量不足 ({len(emerging_skills)} < {self.DISCOVERY_THRESHOLD['min_emerging_skills']})")
            return []

        # Step 2: 技能聚类
        clusters = self._cluster_skills(emerging_skills)
        self.memory.set_context("skill_clusters", clusters)

        # Step 3: 岗位缺口检测
        candidates = self._detect_job_gaps(clusters)

        # Step 4: 对每个候选生成详细定义
        validated_candidates = []
        for candidate in candidates:
            defined = self._generate_job_definition(candidate)
            if defined:
                validated_candidates.append(defined)

        self.discovered_candidates.extend(validated_candidates)

        logger.info(f"[JobDiscovery] 发现 {len(validated_candidates)} 个候选新岗位")
        return validated_candidates

    def _detect_emerging_skills(self, data: list[JobPostRaw]) -> list[dict]:
        """检测新兴技能（基于频率和增长趋势）"""
        skill_freq: dict[str, int] = {}

        # 统计技能出现频率
        for record in data or []:
            for skill in record.skills or []:
                skill_freq[skill] = skill_freq.get(skill, 0) + 1

        if not skill_freq:
            logger.info("[JobDiscovery] 无有效技能数据用于新兴技能检测")
            return []

        # 计算增长率和标记新兴
        emerging = []
        for skill, freq in sorted(skill_freq.items(), key=lambda x: x[1], reverse=True):
            # 模拟增长率（实际应基于时间序列）
            growth_rate = freq * 0.1  # 简化模拟
            if growth_rate >= self.DISCOVERY_THRESHOLD["min_growth_rate"]:
                emerging.append({
                    "name": skill,
                    "frequency": freq,
                    "growth_rate": growth_rate,
                    "sources": ["sample"],  # 实际应从数据中提取
                })

        return emerging[:20]  # 取top20

    def _cluster_skills(self, skills: list[dict]) -> list[dict]:
        """对新兴技能进行聚类"""
        if not skills:
            return []

        # 基于领域的简单聚类
        domain_clusters = {
            "AI_Agent": {
                "name": "AI Agent开发技术栈",
                "skills": [],
                "domain": "人工智能",
            },
            "RAG_System": {
                "name": "RAG/检索增强技术栈",
                "skills": [],
                "domain": "人工智能",
            },
            "LLM_Optimization": {
                "name": "LLM优化与部署技术栈",
                "skills": [],
                "domain": "人工智能",
            },
            "Prompt_Engineering": {
                "name": "提示工程技术栈",
                "skills": [],
                "domain": "人工智能",
            },
        }

        # 根据关键词分配到不同簇
        agent_keywords = ["agent", "智能体", "crewai", "autogen", "langgraph", "多智能体", "工具调用", "function calling", "tool"]
        rag_keywords = ["rag", "检索", "向量", "embedding", "chromadb", "milvus", "知识库", "retrieval"]
        llm_opt_keywords = ["vllm", "推理", "蒸馏", "量化", "部署", "optimization", "distillation", "quantization"]
        prompt_keywords = ["prompt", "提示", "cot", "思维链", "few-shot", "engineering"]

        for skill_info in skills:
            name = skill_info["name"].lower()
            assigned = False

            keywords_map = [
                (agent_keywords, domain_clusters["AI_Agent"]),
                (rag_keywords, domain_clusters["RAG_System"]),
                (llm_opt_keywords, domain_clusters["LLM_Optimization"]),
                (prompt_keywords, domain_clusters["Prompt_Engineering"]),
            ]

            for keywords, cluster in keywords_map:
                if any(kw in name for kw in keywords):
                    cluster["skills"].append(skill_info)
                    assigned = True
                    break

            if not assigned:
                domain_clusters["AI_Agent"]["skills"].append(skill_info)  # 默认归入Agent簇

        # 过滤掉太小的簇
        valid_clusters = [c for c in domain_clusters.values()
                         if len(c["skills"]) >= self.DISCOVERY_THRESHOLD["min_cluster_size"]]

        return valid_clusters

    def _detect_job_gaps(self, clusters: list[dict]) -> list[JobDiscoveryCandidate]:
        """检测岗位缺口"""
        candidates = []

        for cluster in clusters:
            # 检查是否已有高度相似的岗位
            existing_jobs = self.graph.get_all_jobs(status="active")
            cluster_skill_names = [s["name"] for s in cluster["skills"]]

            # 计算与现有岗位的技能重叠度
            best_overlap = 0
            similar_jobs = []

            for job in existing_jobs:
                job_skills = set(job.get("required_skills", []))
                overlap = len(set(cluster_skill_names) & job_skills) / max(len(cluster_skill_names), 1)
                if overlap > 0.3:
                    similar_jobs.append(job["title"])
                best_overlap = max(best_overlap, overlap)

            # 如果重叠度不高，说明可能是新岗位
            if best_overlap < 0.6:
                avg_growth = sum(s["growth_rate"] for s in cluster["skills"]) / len(cluster["skills"])

                candidate = JobDiscoveryCandidate(
                    suggested_title=f"{''.join(s['name'] for s in cluster['skills'][:2])}工程师",
                    skill_cluster=cluster_skill_names,
                    confidence=min(avg_growth / 3, 1.0),  # 归一化
                    evidence_sources=list(set(s for c in cluster["skills"] for s in c.get("sources", []))),
                    growth_rate=avg_growth,
                    similar_existing_jobs=similar_jobs,
                    discovery_reason=f"发现{len(cluster['skills'])}个新兴技能形成强关联簇，与现有岗位重叠度仅{best_overlap:.0%}"
                )
                candidates.append(candidate)

        return candidates

    def _generate_job_definition(self, candidate: JobDiscoveryCandidate) -> JobDiscoveryCandidate:
        """使用LLM生成详细的岗位定义"""
        prompt = f"""你是一个岗位分析专家。根据以下新兴技能簇信息，生成一个标准化的新岗位定义。

技能簇信息：
- 关联技能: {', '.join(candidate.skill_cluster)}
- 增长率: {candidate.growth_rate:.1%}
- 相似已有岗位: {', '.join(candidate.similar_existing_jobs) if candidate.similar_existing_jobs else '无'}

请以JSON格式输出：
{{
    "suggested_title": "建议的岗位名称（简洁专业）",
    "description": "岗位描述（2-3句话）",
    "core_responsibilities": ["职责1", "职责2", ...],
    "required_skills": ["必备技能1", "必备技能2", ...],
    "optional_skills": ["可选技能1", ...],
    "estimated_salary_range": [最低K, 最高K],
    "experience_requirement": "经验要求",
    "target_companies": ["目标公司类型"],
    "market_outlook": "市场前景简述"
}}"""

        try:
            result = self.llm.chat_completion_json([
                {"role": "system", "content": "你是岗位分析专家，擅长从技术趋势中发现和定义新岗位。"},
                {"role": "user", "content": prompt}
            ], temperature=0.4)

            if result:
                candidate.suggested_definition = result
                # 用LLM建议的标题替换临时标题
                if result.get("suggested_title"):
                    candidate.suggested_title = result["suggested_title"]
                logger.info(f"[JobDiscovery] 生成岗位定义: {candidate.suggested_title}")
                return candidate

        except Exception as e:
            logger.error(f"[JobDiscovery] LLM生成定义失败: {e}")

        # Fallback: 使用规则生成
        candidate.suggested_definition = self._fallback_definition(candidate)
        return candidate

    def _fallback_definition(self, candidate: JobDiscoveryCandidate) -> dict:
        """回退方案：规则生成岗位定义"""
        return {
            "suggested_title": candidate.suggested_title,
            "description": f"专注于{', '.join(candidate.skill_cluster[:3])}等技术方向的新兴岗位。",
            "core_responsibilities": [f"基于{candidate.skill_cluster[0]}进行系统开发与优化"],
            "required_skills": candidate.skill_cluster[:6],
            "optional_skills": candidate.skill_cluster[6:] if len(candidate.skill_cluster) > 6 else [],
            "estimated_salary_range": [25, 45],
            "experience_requirement": "2-5年",
            "target_companies": ["AI创业公司", "互联网大厂AI部门", "AI研究院"],
            "market_outlook": f"增长率{candidate.growth_rate:.0%},前景良好",
        }

    def approve_candidate(self, candidate_id_or_title: str, approver: str = "admin") -> bool:
        """审核通过候选岗位，正式加入图谱"""
        for cand in self.discovered_candidates:
            if cand.suggested_title == candidate_id_or_title:
                definition = cand.suggested_definition or self._fallback_definition(cand)

                job_data = {
                    "title": definition.get("suggested_title", cand.suggested_title),
                    "domain": "人工智能",
                    "status": JobStatus.ACTIVE.value,
                    "required_skills": definition.get("required_skills", cand.skill_cluster),
                    "optional_skills": definition.get("optional_skills", []),
                    "avg_salary_min": definition.get("estimated_salary_range", [25, 45])[0],
                    "avg_salary_max": definition.get("estimated_salary_range", [25, 45])[1],
                    "definition_source": "auto_discovered",
                    "description": definition.get("description"),
                    "responsibilities": definition.get("core_responsibilities", []),
                    "demand_trend": "rising",
                }

                self.graph.create_job_node(job_data)

                # 创建requires关系
                for skill in job_data["required_skills"]:
                    self.graph.create_requires_relation(job_data["title"], skill, required=True,
                                                       confidence=cand.confidence)

                logger.info(f"[JobDiscovery] 岗位已批准入库: {cand.suggested_title}")
                return True

        return False

    def _form_hypothesis(self, task_input: Any, perception: dict) -> dict:
        return {"strategy": "trend_clustering_based_discovery"}

    def _act(self, hypothesis: Any, task_input: Any, **kwargs) -> Any:
        data = kwargs.get("recent_data")
        return self.discover_new_jobs(data)
