"""数据采集Agent - 从互联网搜索引擎实时采集真实招聘数据"""

import logging
import time
from datetime import datetime
from typing import Any
from .base_agent import BaseKnowledgeAgent
from models.job_model import JobPostSource, JobPostRaw
from core.data_pipeline import DataPipeline
from config.settings import get_settings

logger = logging.getLogger(__name__)


class DataCollectorAgent(BaseKnowledgeAgent):
    """数据采集Agent - 通过搜索引擎实时采集招聘数据"""

    agent_name = "data_collector"
    agent_description = "从搜索引擎实时采集真实招聘数据"

    # 要搜索的招聘领域关键词（覆盖新一代信息技术各大方向）
    JOB_KEYWORDS = [
        # ===== 人工智能 =====
        "AI算法工程师", "机器学习工程师", "深度学习工程师", "NLP算法工程师",
        "计算机视觉工程师", "推荐算法工程师", "大模型工程师", "LLM应用开发",
        "AI产品经理", "AI研究员", "语音算法工程师", "知识图谱工程师",

        # ===== 大数据 =====
        "数据分析师", "大数据开发工程师", "数据仓库工程师", "数据挖掘工程师",
        "数据科学家", "ETL工程师", "实时计算工程师", "Flink开发工程师",
        "Spark开发工程师", "数据治理工程师", "BI工程师", "数据运营",

        # ===== 软件开发 =====
        "Java开发工程师", "Python开发工程师", "Go开发工程师", "C++开发工程师",
        "C#开发工程师", "Rust开发工程师", "后端开发工程师", "全栈工程师",
        "架构师", "技术经理", "研发总监", "技术专家",

        # ===== 前端开发 =====
        "前端开发工程师", "Web前端工程师", "React开发工程师", "Vue开发工程师",
        "小程序开发工程师", "H5开发工程师", "前端架构师", "UI开发工程师",
        "Node.js开发工程师", "TypeScript开发工程师",

        # ===== 移动开发 =====
        "iOS开发工程师", "Android开发工程师", "Flutter开发工程师",
        "React Native开发工程师", "移动端开发工程师", "App开发工程师",

        # ===== 云计算与DevOps =====
        "云计算工程师", "云架构师", "DevOps工程师", "SRE工程师",
        "运维开发工程师", "容器工程师", "K8s运维工程师", "云原生工程师",
        "基础设施工程师", "平台工程师", "自动化运维工程师",

        # ===== 网络安全 =====
        "网络安全工程师", "信息安全工程师", "渗透测试工程师", "安全运维工程师",
        "安全研究员", "安全架构师", "数据安全工程师", "安全分析师",
        "漏洞挖掘工程师", "应急响应工程师", "安全合规工程师",

        # ===== 区块链与Web3 =====
        "区块链开发工程师", "智能合约工程师", "Web3开发工程师",
        "Solidity开发工程师", "DeFi开发工程师", "区块链架构师",

        # ===== 物联网与嵌入式 =====
        "嵌入式开发工程师", "物联网工程师", "IoT开发工程师",
        "嵌入式软件工程师", "嵌入式硬件工程师", "驱动开发工程师",
        "RTOS开发工程师", "边缘计算工程师",

        # ===== 测试与质量 =====
        "测试工程师", "测试开发工程师", "自动化测试工程师",
        "性能测试工程师", "安全测试工程师", "QA工程师",

        # ===== 产品与设计 =====
        "产品经理", "数据产品经理", "技术产品经理", "UX设计师",
        "UI设计师", "交互设计师", "产品运营",

        # ===== 数据库与中间件 =====
        "数据库工程师", "DBA", "MySQL工程师", "PostgreSQL工程师",
        "MongoDB工程师", "Redis工程师", "Elasticsearch工程师",
        "消息队列工程师", "中间件工程师",
    ]

    def __init__(self):
        super().__init__()
        self.settings = get_settings()
        self.pipeline = DataPipeline()
        self._collection_stats = {
            "total_collected": 0,
            "last_collection": None,
            "by_source": {},
        }

    def _setup_tools(self):
        pass

    def _form_hypothesis(self, task_input, perception):
        action = task_input.get("action", "collect_all")
        return {"action": action}

    def _act(self, hypothesis, task_input, **kwargs):
        action = hypothesis["action"]
        if action == "collect_all":
            return self.collect_all_sources()
        elif action == "collect_and_build":
            return self.collect_and_build_graph()
        return {"success": False, "error": f"Unknown action: {action}"}

    def collect_all_sources(self):
        """采集所有数据源 - 通过搜索引擎实时搜索"""
        results = {}
        total_records = []

        logger.info("=== 开始多关键词招聘数据采集 ===")
        web_data = self._collect_from_real_web()
        if web_data:
            total_records.extend(web_data)
            results["web_search"] = {"count": len(web_data), "status": "success"}
            self._collection_stats["by_source"]["web_search"] = len(web_data)
        else:
            results["web_search"] = {"count": 0, "status": "no_data"}
            self._collection_stats["by_source"]["web_search"] = 0

        if total_records:
            processed = self.pipeline.deduplicate(total_records)
        else:
            processed = []

        self._collection_stats["total_collected"] = len(processed)
        self._collection_stats["last_collection"] = datetime.now().isoformat()

        return {
            "sources": results,
            "total_raw": len(total_records),
            "total_deduplicated": len(processed),
            "stats": self._collection_stats,
            "processed_data": processed,
        }

    def _collect_from_real_web(self) -> list[JobPostRaw]:
        """从搜索引擎实时搜索招聘信息"""
        all_records = []

        try:
            from tools.web_search_tool import WebSearchTool
            searcher = WebSearchTool()

            search_jobs = searcher.search_jobs_multiple_keywords(
                self.JOB_KEYWORDS,
                count_per_keyword=5
            )

            if not search_jobs:
                logger.warning("搜索引擎未返回任何招聘数据")
                return []

            logger.info(f"搜索引擎返回 {len(search_jobs)} 条原始招聘信息")

            for job in search_jobs:
                try:
                    source = JobPostSource.WEB_SEARCH
                    processed = self.pipeline.process_raw_data(job, source)

                    if job.get("source_url"):
                        processed.job_description = (processed.job_description or "") + f"\n来源URL: {job['source_url']}"

                    all_records.append(processed)
                except Exception as e:
                    logger.debug(f"处理单条搜索数据失败: {e}")

            logger.info(f"搜索引擎采集完成，共处理 {len(all_records)} 条数据")
            return all_records

        except Exception as e:
            logger.error(f"搜索引擎搜索失败: {e}")
            return []

    def enhance_search_results_with_llm(self, raw_jobs: list[JobPostRaw]) -> list[JobPostRaw]:
        """使用LLM增强搜索结果：为岗位推断技能要求、薪资范围等"""
        if not raw_jobs:
            return []

        try:
            from core.llm_service import get_llm_service
            llm = get_llm_service()

            if not llm.is_ready:
                logger.warning("LLM未就绪，跳过搜索结果增强")
                return raw_jobs

            enhanced_count = 0
            for job in raw_jobs:
                if job.skills:
                    continue

                messages = [
                    {"role": "system", "content": "你是一位IT行业招聘专家。请严格按照要求的JSON格式输出，不要添加任何额外文字。"},
                    {"role": "user", "content": (
                        f"请分析以下岗位，推断该岗位最可能需要的核心技术技能（5-8个），"
                        f"以及合理的薪资范围。只返回JSON格式。\n\n"
                        f"岗位: {job.job_title}\n"
                        f"公司: {job.company_name or '未知'}\n\n"
                        f"格式: {{\"skills\": [\"技能1\", \"技能2\", ...], \"salary_min\": XX, \"salary_max\": XX}}"
                    )}
                ]

                result = llm.chat_completion_json(messages)
                if result:
                    if "skills" in result and isinstance(result["skills"], list):
                        job.skills = [s.strip() for s in result["skills"] if s.strip()]
                    if "salary_min" in result and result["salary_min"]:
                        job.salary_min = int(result["salary_min"])
                    if "salary_max" in result and result["salary_max"]:
                        job.salary_max = int(result["salary_max"])
                    enhanced_count += 1

                time.sleep(0.3)

            logger.info(f"LLM增强完成: {enhanced_count}/{len(raw_jobs)} 条数据已补充技能信息")
            return raw_jobs

        except Exception as e:
            logger.warning(f"LLM增强失败: {e}")
            return raw_jobs

    def collect_and_build_graph(self) -> dict:
        """完整流程：采集→解析→构建图谱"""
        logger.info("=== 开始完整数据采集与图谱构建流程 ===")

        collection = self.collect_all_sources()
        raw_jds = collection.get("processed_data", [])

        if not raw_jds:
            logger.warning("未采集到任何数据")
            return {
                "success": False,
                "reason": "no_data",
                "message": "未从网络采集到任何岗位数据"
            }

        logger.info(f"采集完成：{len(raw_jds)} 条岗位数据")

        enhanced = self.enhance_search_results_with_llm(raw_jds)

        from agents.graph_builder import GraphBuilderAgent
        builder = GraphBuilderAgent()
        build_result = builder.build_from_data([
            {
                "job_title": r.job_title,
                "company_name": r.company_name or "",
                "skills": r.skills or [],
                "salary_min": r.salary_min,
                "salary_max": r.salary_max,
                "location": r.location or "",
                "source": r.source.value if hasattr(r.source, 'value') else str(r.source),
            }
            for r in enhanced
        ])

        return {
            "success": True,
            "collected_raw": len(raw_jds),
            "enhanced_count": len(enhanced),
            "graph_build": build_result,
            "message": f"采集{len(raw_jds)}条数据，成功写入Neo4j图谱",
        }
