"""编排中心Agent - 负责任务分解、Agent调度、结果汇总、质量把关"""

import asyncio
import logging
from typing import Any, Optional
from .base_agent import BaseKnowledgeAgent, AgentMemory

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseKnowledgeAgent):
    """编排中心Agent

    职责：
    1. 接收用户任务，理解意图
    2. 分解为子任务
    3. 分配给合适的专业Agent
    4. 监控执行进度
    5. 汇总结果并进行质量把关
    """

    agent_name = "orchestrator"
    agent_description = "任务编排中心 - 协调各专业Agent协作完成复杂任务"

    def __init__(self, agent_registry: dict = None):
        super().__init__()
        self.agent_registry = agent_registry or {}
        self.task_history: list[dict] = []

    def register_agent(self, agent_instance: BaseKnowledgeAgent):
        """注册专业Agent"""
        self.agent_registry[agent_instance.agent_name] = agent_instance
        logger.info(f"编排中心注册Agent: {agent_instance.agent_name}")

    def _setup_tools(self):
        """编排中心不需要特殊工具"""
        pass

    def orchestrate(self, user_request: str, context: dict = None) -> dict:
        """编排执行用户请求的主入口"""
        context = context or {}
        self.memory.set_context("user_request", user_request)
        logger.info(f"=== 编排中心收到请求: {user_request[:100]}... ===")

        # Step 1: 理解任务意图
        intent = self._analyze_intent(user_request)
        self.memory.set_context("intent", intent)

        # Step 2: 任务分解
        sub_tasks = self._decompose_task(intent, user_request)
        self.memory.set_context("sub_tasks", sub_tasks)

        if not sub_tasks:
            return {
                "success": False,
                "error": "无法理解任务意图或无法分解为可执行的子任务",
                "intent": intent,
            }

        # Step 3: 分配Agent
        assignments = self._assign_agents(sub_tasks)

        # Step 4: 执行子任务
        results = self._execute_subtasks(assignments, context)

        # Step 5: 结果汇总与质量把关
        final_output = self._synthesize_results(results, sub_tasks, user_request)

        # 记录历史
        self.task_history.append({
            "request": user_request[:200],
            "intent": intent,
            "subtask_count": len(sub_tasks),
            "success": final_output.get("success", False),
            "timestamp": __import__('datetime').datetime.now().isoformat(),
        })

        return final_output

    def _analyze_intent(self, request: str) -> dict:
        """分析用户请求意图"""
        request_lower = request.lower()

        # 关键词匹配确定任务类型
        intent_rules = {
            "resume_analysis": ["简历", "解析简历", "上传简历", "分析简历", "resume"],
            "job_matching": ["匹配", "岗位匹配", "推荐岗位", "适合什么工作", "matching"],
            "gap_analysis": ["差距", "不足", "缺什么", "需要学什么", "gap"],
            "job_discovery": ["新岗位", "发现岗位", "新兴岗位", "新职业", "discovery"],
            "data_collection": ["采集", "爬取", "更新数据", "数据源", "collect"],
            "graph_operation": ["图谱", "知识图谱", "技能关系", "graph"],
            "career_path": ["职业规划", "发展路径", "转行", "career"],
            "market_analysis": ["市场", "薪资", "趋势", "行情", "market"],
            "what_if": ["如果", "假设", "学了.*会怎样", "what if"],
            "qa_question": ["什么是", "如何", "为什么", "哪个好", "?"],
        }

        detected_intents = []
        scores = {}
        for intent_type, keywords in intent_rules.items():
            import re
            score = 0
            for kw in keywords:
                try:
                    if re.search(kw, request_lower):
                        score += 1
                except re.error:
                    if kw in request_lower:
                        score += 1
            if score > 0:
                detected_intents.append(intent_type)
                scores[intent_type] = score

        primary_intent = max(scores.keys(), key=lambda k: scores[k]) if scores else "general"

        return {
            "primary": primary_intent,
            "all_detected": detected_intents,
            "confidence_scores": scores,
            "complexity": "simple" if len(detected_intents) <= 1 else "complex",
        }

    def _decompose_task(self, intent: dict, request: str) -> list[dict]:
        """将意图分解为可执行的子任务"""
        primary = intent["primary"]
        tasks = []

        task_templates = {
            "resume_analysis": [
                {"step": 1, "agent": "resume_parser", "action": "parse_resume", "desc": "解析简历文件"},
                {"step": 2, "agent": "resume_parser", "action": "extract_skills", "desc": "提取技能信息"},
                {"step": 3, "agent": "resume_parser", "action": "assess_credibility", "desc": "评估技能可信度"},
            ],
            "job_matching": [
                {"step": 1, "agent": "resume_parser", "action": "parse_resume", "desc": "解析简历"},
                {"step": 2, "agent": "matching_agent", "action": "find_matches", "desc": "查找匹配岗位"},
                {"step": 3, "agent": "matching_agent", "action": "rank_results", "desc": "排序匹配结果"},
                {"step": 4, "agent": "gap_analyzer", "action": "analyze_gaps", "desc": "分析能力差距"},
            ],
            "gap_analysis": [
                {"step": 1, "agent": "resume_parser", "action": "parse_resume", "desc": "解析简历"},
                {"step": 2, "agent": "gap_analyzer", "action": "full_gap_analysis", "desc": "全面差距分析"},
                {"step": 3, "agent": "gap_analyzer", "action": "generate_learning_path", "desc": "生成学习路径"},
            ],
            "job_discovery": [
                {"step": 1, "agent": "data_collector", "action": "collect_latest_data", "desc": "采集最新数据"},
                {"step": 2, "agent": "job_discovery", "action": "discover_new_jobs", "desc": "发现候选新岗位"},
                {"step": 3, "agent": "job_discovery", "action": "validate_candidates", "desc": "验证候选岗位"},
            ],
            "data_collection": [
                {"step": 1, "agent": "data_collector", "action": "collect_latest_data", "desc": "采集多源招聘数据"},
                {"step": 2, "agent": "graph_builder", "action": "build_from_data", "desc": "构建知识图谱"},
            ],
            "graph_operation": [
                {"step": 1, "agent": "graph_builder", "action": "init_graph", "desc": "查询/初始化图谱"},
            ],
            "market_analysis": [
                {"step": 1, "agent": "data_collector", "action": "collect_latest_data", "desc": "采集市场数据"},
                {"step": 2, "agent": "job_discovery", "action": "validate_candidates", "desc": "分析市场趋势"},
            ],
            "qa_question": [
                {"step": 1, "agent": "orchestrator", "action": "handle_general_query", "desc": "处理通用查询"},
            ],
            "what_if": [
                {"step": 1, "agent": "resume_parser", "action": "parse_resume", "desc": "解析当前简历"},
                {"step": 2, "agent": "matching_agent", "action": "simulate_match", "desc": "模拟假设性匹配"},
            ],
            "career_path": [
                {"step": 1, "agent": "resume_parser", "action": "parse_resume", "desc": "解析简历"},
                {"step": 2, "agent": "gap_analyzer", "action": "analyze_career_paths", "desc": "分析职业路径"},
            ],
            "general": [
                {"step": 1, "agent": "orchestrator", "action": "handle_general_query", "desc": "处理通用查询"},
            ],
        }

        template = task_templates.get(primary, task_templates["general"])
        for t in template:
            tasks.append({**t, "request": request})

        return tasks

    def _assign_agents(self, sub_tasks: list[dict]) -> list[tuple]:
        """将子任务分配给对应的Agent实例"""
        assignments = []
        for task in sub_tasks:
            agent_name = task["agent"]
            agent = self.agent_registry.get(agent_name)
            if agent:
                assignments.append((task, agent))
            else:
                logger.warning(f"Agent [{agent_name}] 未注册，跳过任务: {task['desc']}")
        return assignments

    def _execute_subtasks(self, assignments: list[tuple], context: dict) -> list[dict]:
        """按依赖顺序执行子任务"""
        results = []

        for task, agent in assignments:
            logger.info(f"  → 执行 Step {task['step']}: {task['desc']} (Agent: {agent.agent_name})")

            try:
                result = agent.execute(task, **context)
                results.append({
                    "task": task,
                    "result": result,
                    "status": "completed" if result.get("success") else "failed",
                })

                # 将中间结果传递给后续任务
                if result.get("result"):
                    context[f"step_{task['step']}_output"] = result["result"]

            except Exception as e:
                logger.error(f"  ✗ 子任务执行失败: {e}")
                results.append({
                    "task": task,
                    "result": {"success": False, "error": str(e)},
                    "status": "error",
                })

        return results

    def _synthesize_results(self, results: list[dict], sub_tasks: list[dict],
                            original_request: str) -> dict:
        """汇总所有子任务结果"""
        successful = [r for r in results if r["status"] == "completed"]
        failed = [r for r in results if r["status"] != "completed"]

        all_outputs = {}
        for r in successful:
            step_key = f"step_{r['task']['step']}"
            all_outputs[step_key] = r["result"].get("result")

        synthesis = {
            "success": len(failed) == 0,
            "original_request": original_request[:200],
            "total_steps": len(sub_tasks),
            "completed_steps": len(successful),
            "failed_steps": len(failed),
            "outputs": all_outputs,
        }

        if failed:
            synthesis["errors"] = [
                {"step": r["task"]["step"], "desc": r["task"]["desc"],
                 "error": r["result"].get("error", "未知错误")}
                for r in failed
            ]

        # 质量概要
        synthesis["quality_summary"] = {
            "completion_rate": len(successful) / max(len(sub_tasks), 1),
            "has_errors": len(failed) > 0,
            "recommendation": "全部完成" if not failed else f"{len(successful)}/{len(sub_tasks)}步骤完成",
        }

        return synthesis

    def _form_hypothesis(self, task_input: Any, perception: dict) -> dict:
        return {"plan": "按照预定义的任务模板执行编排"}

    def _act(self, hypothesis: Any, task_input: Any, **kwargs) -> Any:
        request = kwargs.get("user_request") or getattr(task_input, 'get', lambda k: {})('request', '')
        if isinstance(task_input, dict) and 'request' in task_input:
            request = task_input['request']
        return self.orchestrate(request or str(task_input), kwargs)
