"""Agent基类 - 提供工具调用、记忆系统、自反思能力"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional
from langchain_core.tools import BaseTool
from core.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class AgentMemory:
    """三层记忆架构（长期记忆+实体记忆持久化到SQLite）"""

    def __init__(self, agent_name: str = "base_agent"):
        self.agent_name = agent_name
        self.short_term: dict = {}      # 当前任务上下文（内存）
        self.long_term: list[dict] = []  # 历史决策模式（内存缓存）
        self.entity_memory: dict = {}   # 跨会话实体跟踪（内存缓存）
        self._db = None  # 延迟加载DB

    @property
    def db(self):
        """延迟加载DB单例"""
        if self._db is None:
            try:
                from backend.storage import get_db
                self._db = get_db()
            except Exception as e:
                logger.debug(f"DB加载失败，记忆将仅存内存: {e}")
                self._db = False  # 标记不可用
        return self._db if self._db is not False else None

    def set_context(self, key: str, value: Any):
        """设置短期记忆"""
        self.short_term[key] = value

    def get_context(self, key: str, default=None):
        """获取短期记忆"""
        return self.short_term.get(key, default)

    def add_experience(self, task_type: str, decision: str, outcome: str,
                       success: bool, lesson: str = ""):
        """记录长期经验（同时写入内存和SQLite）"""
        # 内存缓存
        self.long_term.append({
            "task_type": task_type,
            "decision": decision,
            "outcome": outcome,
            "success": success,
            "lesson": lesson,
            "timestamp": datetime.now().isoformat(),
        })
        # 保留最近100条内存经验
        if len(self.long_term) > 100:
            self.long_term = self.long_term[-100:]

        # 持久化到SQLite
        if self.db:
            try:
                self.db.save_agent_experience(
                    agent_name=self.agent_name,
                    task_type=task_type,
                    decision=decision,
                    outcome=outcome,
                    success=success,
                    lesson=lesson,
                )
            except Exception as e:
                logger.debug(f"经验持久化失败: {e}")

    def get_similar_experiences(self, task_type: str, limit: int = 5) -> list[dict]:
        """获取相似任务的历史经验（优先从SQLite加载）"""
        # 内存有则用内存
        if self.long_term:
            experiences = [e for e in self.long_term if e["task_type"] == task_type]
            return experiences[-limit:]

        # 内存无则从SQLite加载
        if self.db:
            try:
                rows = self.db.get_agent_experiences(
                    agent_name=self.agent_name,
                    task_type=task_type,
                    limit=limit,
                )
                # 转换为兼容格式
                return [{
                    "task_type": r["task_type"],
                    "decision": r["decision"],
                    "outcome": r["outcome"],
                    "success": bool(r["success"]),
                    "lesson": r["lesson"],
                    "timestamp": r["created_at"],
                } for r in rows]
            except Exception as e:
                logger.debug(f"从DB加载经验失败: {e}")
        return []

    def track_entity(self, entity_id: str, entity_type: str, **attrs):
        """跟踪实体变化（同时写入内存和SQLite）"""
        # 内存缓存
        if entity_id not in self.entity_memory:
            self.entity_memory[entity_id] = {
                "type": entity_type,
                "first_seen": datetime.now().isoformat(),
                "versions": [],
            }
        self.entity_memory[entity_id]["versions"].append({
            **attrs,
            "updated_at": datetime.now().isoformat(),
        })

        # 持久化到SQLite
        if self.db:
            try:
                self.db.track_agent_entity(
                    agent_name=self.agent_name,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    attrs=attrs,
                )
            except Exception as e:
                logger.debug(f"实体跟踪持久化失败: {e}")

    def get_entity_history(self, entity_id: str) -> Optional[dict]:
        """获取实体的历史记录（优先从SQLite加载）"""
        # 内存有则用内存
        if entity_id in self.entity_memory:
            return self.entity_memory[entity_id]

        # 内存无则从SQLite加载
        if self.db:
            try:
                return self.db.get_agent_entity_history(self.agent_name, entity_id)
            except Exception as e:
                logger.debug(f"从DB加载实体历史失败: {e}")
        return None

    def clear_short_term(self):
        """清除短期记忆（新任务开始时调用）"""
        self.short_term = {}


class BaseKnowledgeAgent(ABC):
    """知识图谱系统Agent基类

    每个Agent具备：
    1. 工具调用能力 (Tool-Use)
    2. 记忆系统 (Memory): 短期/长期/实体
    3. 自反思机制 (Self-Reflection)
    """

    agent_name: str = "base_agent"
    agent_description: str = "基础Agent"
    agent_version: str = "1.0"

    def __init__(self):
        self.llm = get_llm_service()
        self.memory = AgentMemory(agent_name=self.agent_name)
        self.tools: dict[str, BaseTool] = {}
        self._setup_tools()

        # 运行统计
        self.stats = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "avg_reflection_rounds": 0,
            "total_reflections": 0,
        }

    @abstractmethod
    def _setup_tools(self):
        """子类实现：配置Agent专属工具集"""
        pass

    def register_tool(self, name: str, tool: BaseTool):
        """注册工具"""
        self.tools[name] = tool
        logger.debug(f"[{self.agent_name}] 注册工具: {name}")

    def execute(self, task_input: Any, **kwargs) -> dict:
        """执行任务的入口方法（带反思循环）"""
        self.memory.clear_short_term()
        self.memory.set_context("task_input", task_input)
        self.memory.set_context("start_time", datetime.now().isoformat())

        logger.info(f"[{self.agent_name}] 开始执行任务")

        try:
            # 反思循环：感知→假设→验证→行动→反思→输出
            result = self._reflection_loop(task_input, **kwargs)

            self.stats["tasks_completed"] += 1
            return result

        except Exception as e:
            logger.error(f"[{self.agent_name}] 任务执行失败: {e}", exc_info=True)
            self.stats["tasks_failed"] += 1

            # 记录失败经验
            self.memory.add_experience(
                task_type=self.agent_name,
                decision="execute_task",
                outcome=str(e),
                success=False,
                lesson=f"执行失败原因: {str(e)[:200]}"
            )

            return {"success": False, "error": str(e), "agent": self.agent_name}

    def _reflection_loop(self, task_input: Any, max_rounds: int = 3, **kwargs) -> dict:
        """自反思循环

        流程：
        1. 感知 - 观察当前状态和数据
        2. 假设 - 形成初步判断或方案
        3. 验证 - 查询已有知识或外部验证
        4. 行动 - 执行具体操作
        5. 反思 - 评估结果质量
        6. 输出 - 提交高质量结果
        """
        current_result = None
        confidence = 0.0

        for round_num in range(1, max_rounds + 1):
            self.memory.set_context("reflection_round", round_num)
            logger.debug(f"[{self.agent_name}] 反思轮次 {round_num}/{max_rounds}")

            # Step 1 & 2: 感知 + 假设
            perception = self._perceive(task_input)
            hypothesis = self._form_hypothesis(task_input, perception)
            self.memory.set_context("hypothesis", hypothesis)

            # Step 3: 验证
            validation = self._validate(hypothesis, task_input)
            self.memory.set_context("validation", validation)

            if not validation.get("valid", True):
                # 验证不通过，调整后重试
                adjusted = self._adjust(hypothesis, validation)
                hypothesis = adjusted
                self.memory.set_context("adjusted_hypothesis", hypothesis)

            # Step 4: 行动
            action_result = self._act(hypothesis, task_input, **kwargs)
            current_result = action_result

            # Step 5: 反思
            reflection = self._reflect(action_result, hypothesis)
            confidence = reflection.get("confidence", 0.5)
            self.stats["total_reflections"] += 1

            # 记录经验
            self.memory.add_experience(
                task_type=self.agent_name,
                decision=str(hypothesis)[:100],
                outcome=str(action_result)[:200] if isinstance(action_result, dict) else str(action_result)[:200],
                success=confidence > 0.7,
                lesson=reflection.get("lesson", "")
            )

            # 如果置信度足够高，提前结束
            if confidence >= 0.85:
                logger.info(f"[{self.agent_name}] 第{round_num}轮置信度达标({confidence:.0%})，结束反思")
                break

        # 更新平均反思轮次
        total_tasks = self.stats["tasks_completed"] + self.stats["tasks_failed"] + 1
        self.stats["avg_reflection_rounds"] = (
            (self.stats["avg_reflection_rounds"] * (total_tasks - 1) +
             self.memory.get_context("reflection_round", 1)) / total_tasks
        )

        return {
            "success": True,
            "result": current_result,
            "confidence": confidence,
            "agent": self.agent_name,
            "reflection_rounds": self.memory.get_context("reflection_round", 1),
        }

    def _perceive(self, task_input: Any) -> dict:
        """Step 1: 感知 - 观察当前状态和数据"""
        return {
            "input_summary": str(task_input)[:500] if task_input else "",
            "available_tools": list(self.tools.keys()),
            "timestamp": datetime.now().isoformat(),
        }

    @abstractmethod
    def _form_hypothesis(self, task_input: Any, perception: dict) -> Any:
        """Step 2: 形成初步判断/方案"""
        pass

    def _validate(self, hypothesis: Any, task_input: Any) -> dict:
        """Step 3: 验证假设的合理性"""
        # 默认验证逻辑：检查假设是否为空
        if hypothesis is None:
            return {"valid": False, "reason": "假设为空"}
        return {"valid": True}

    def _adjust(self, hypothesis: Any, validation: dict) -> Any:
        """验证不通过时的调整策略"""
        return hypothesis  # 默认不做调整

    @abstractmethod
    def _act(self, hypothesis: Any, task_input: Any, **kwargs) -> Any:
        """Step 4: 执行具体操作"""
        pass

    def _reflect(self, action_result: Any, hypothesis: Any) -> dict:
        """Step 5: 评估结果质量"""
        if action_result is None:
            return {"confidence": 0.0, "lesson": "操作返回None"}

        if isinstance(action_result, dict):
            has_content = any(v for v in action_result.values() if v)
            return {
                "confidence": 0.8 if has_content else 0.3,
                "lesson": "" if has_content else "结果内容为空",
            }

        return {"confidence": 0.7, "lesson": ""}

    def think(self, question: str) -> str:
        """使用LLM进行深度思考"""
        messages = [
            {"role": "system", "content": f"你是{self.agent_description}。请深入思考并回答问题。"},
            {"role": "user", "content": question},
        ]
        return self.llm.chat_completion(messages, temperature=0.5)

    def use_tool(self, tool_name: str, **kwargs) -> Any:
        """调用已注册的工具"""
        if tool_name not in self.tools:
            logger.warning(f"[{self.agent_name}] 工具[{tool_name}]未注册")
            return None

        tool = self.tools[tool_name]
        try:
            result = tool.invoke(kwargs)
            logger.debug(f"[{self.agent_name}] 工具[{tool_name}]调用成功")
            return result
        except Exception as e:
            logger.error(f"[{self.agent_name}] 工具[{tool_name}]调用失败: {e}")
            return None

    def get_stats(self) -> dict:
        """获取运行统计"""
        return {
            "agent": self.agent_name,
            "version": self.agent_version,
            **self.stats,
            "memory_size": {
                "short_term": len(self.memory.short_term),
                "long_term": len(self.memory.long_term),
                "entities": len(self.memory.entity_memory),
            },
        }
