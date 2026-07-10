"""Agent模块测试 - 记忆系统、编排中心、图谱构建"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


# ========== Agent记忆系统测试 ==========

class TestBaseAgentMemory:
    """测试Agent记忆系统"""

    @pytest.fixture
    def memory(self):
        from agents.base_agent import AgentMemory
        return AgentMemory()

    def test_short_term_memory(self, memory):
        """测试短期记忆读写"""
        memory.set_context("current_task", "数据分析")
        assert memory.get_context("current_task") == "数据分析"
        assert memory.get_context("non_existent", "默认值") == "默认值"

        memory.set_context("key_int", 42)
        memory.set_context("key_list", [1, 2, 3])
        memory.set_context("key_dict", {"a": 1})
        assert memory.get_context("key_int") == 42
        assert memory.get_context("key_list") == [1, 2, 3]
        assert memory.get_context("key_dict") == {"a": 1}

    def test_long_term_memory(self, memory):
        """测试长期记忆读写"""
        memory.add_experience(
            task_type="resume_analysis",
            decision="extract_skills_from_text",
            outcome="成功提取23个技能",
            success=True,
            lesson="使用正则+LSTM效果较好",
        )
        memory.add_experience(
            task_type="resume_analysis",
            decision="match_jobs",
            outcome="找到5个匹配岗位",
            success=True,
            lesson="技能权重需要调整",
        )
        memory.add_experience(
            task_type="data_collection",
            decision="scrape_website",
            outcome="连接超时",
            success=False,
            lesson="需要增加重试机制",
        )

        experiences = memory.get_similar_experiences("resume_analysis")
        assert len(experiences) == 2
        assert all(e["task_type"] == "resume_analysis" for e in experiences)

        assert memory.get_similar_experiences("non_existent") == []

        data_exp = memory.get_similar_experiences("data_collection")
        assert len(data_exp) == 1
        assert data_exp[0]["success"] is False

    def test_long_term_capacity(self, memory):
        """测试长期记忆容量限制"""
        for i in range(150):
            memory.add_experience(
                task_type="test", decision=f"decision_{i}",
                outcome="ok", success=True,
            )
        assert len(memory.long_term) <= 100

    def test_entity_memory(self, memory):
        """测试实体记忆"""
        memory.track_entity("张三", "person", title="工程师", level="senior")
        memory.track_entity("张三", "person", title="架构师", level="staff")

        history = memory.get_entity_history("张三")
        assert history is not None
        assert history["type"] == "person"
        assert len(history["versions"]) == 2

        assert memory.get_entity_history("不存在") is None

    def test_clear_short_term(self, memory):
        """测试短期记忆清除"""
        memory.set_context("key1", "value1")
        memory.set_context("key2", "value2")
        assert len(memory.short_term) == 2

        memory.clear_short_term()
        assert len(memory.short_term) == 0

    def test_agent_stats(self):
        """测试Agent统计信息"""
        from agents.base_agent import BaseKnowledgeAgent

        with patch('agents.base_agent.get_llm_service') as mock_llm:
            mock_llm.return_value = MagicMock()

            class TestAgent(BaseKnowledgeAgent):
                agent_name = "test_agent"

                def _setup_tools(self):
                    pass

                def _form_hypothesis(self, task_input, perception):
                    return {"action": "test"}

                def _act(self, hypothesis, task_input, **kwargs):
                    return {"done": True}

            agent = TestAgent()
            stats = agent.get_stats()

            assert "agent" in stats
            assert stats["agent"] == "test_agent"
            assert "memory_size" in stats
            assert stats["memory_size"]["short_term"] == 0


# ========== 编排中心测试 ==========

class TestOrchestratorIntent:
    """测试编排中心意图识别"""

    @pytest.fixture
    def orchestrator(self):
        from agents.orchestrator import OrchestratorAgent
        with patch('agents.base_agent.get_llm_service') as mock_llm:
            mock_llm.return_value = MagicMock()
            return OrchestratorAgent()

    def test_intent_resume_analysis(self, orchestrator):
        """测试简历分析意图"""
        intent = orchestrator._analyze_intent("帮我分析这份简历")
        assert intent["primary"] == "resume_analysis"
        assert "resume_analysis" in intent["all_detected"]

        intent2 = orchestrator._analyze_intent("解析简历并提取技能")
        assert intent2["primary"] == "resume_analysis"

    def test_intent_job_matching(self, orchestrator):
        """测试岗位匹配意图"""
        intent = orchestrator._analyze_intent("帮我匹配最适合的岗位")
        assert intent["primary"] == "job_matching"

    def test_intent_gap_analysis(self, orchestrator):
        """测试差距分析意图"""
        intent = orchestrator._analyze_intent("分析我的技能差距")
        assert intent["primary"] == "gap_analysis"

    def test_intent_data_collection(self, orchestrator):
        """测试数据采集意图"""
        intent = orchestrator._analyze_intent("采集最新的岗位数据")
        assert intent["primary"] == "data_collection"

    def test_intent_market_analysis(self, orchestrator):
        """测试市场分析意图"""
        intent = orchestrator._analyze_intent("当前市场的薪资趋势如何")
        assert intent["primary"] == "market_analysis"

    def test_intent_career_path(self, orchestrator):
        """测试职业规划意图"""
        intent = orchestrator._analyze_intent("我的职业发展路径应该是怎样的")
        assert intent["primary"] == "career_path"

    def test_intent_unknown(self, orchestrator):
        """测试未知意图"""
        intent = orchestrator._analyze_intent("你好")
        assert intent["primary"] in ["general", "qa_question"]

    def test_intent_complexity(self, orchestrator):
        """测试复杂度判断"""
        simple_intent = orchestrator._analyze_intent("帮我解析简历")
        assert simple_intent["complexity"] == "simple"

        complex_intent = orchestrator._analyze_intent("帮我解析简历并匹配岗位，分析差距")
        assert complex_intent["complexity"] == "complex"

    def test_task_decomposition(self, orchestrator):
        """测试任务分解"""
        intent = {"primary": "resume_analysis", "all_detected": ["resume_analysis"], "confidence_scores": {"resume_analysis": 1}, "complexity": "simple"}
        tasks = orchestrator._decompose_task(intent, "帮我分析简历")
        assert len(tasks) >= 1
        assert tasks[0]["agent"] == "resume_parser"

    def test_orchestrate_no_agents(self, orchestrator):
        """测试无Agent注册时的编排"""
        result = orchestrator.orchestrate("帮我分析简历")
        assert "success" in result or "error" in result

    def test_register_agent(self, orchestrator):
        """测试注册Agent"""
        mock_agent = MagicMock()
        mock_agent.agent_name = "resume_parser"
        orchestrator.register_agent(mock_agent)
        assert "resume_parser" in orchestrator.agent_registry


# ========== 图谱构建测试 ==========

class TestGraphBuilderSeed:
    """测试图谱构建的种子数据加载"""

    @pytest.fixture
    def builder(self):
        from agents.graph_builder import GraphBuilderAgent
        with patch('agents.graph_builder.get_llm_service') as mock_llm, \
             patch('agents.graph_builder.get_graph_service') as mock_graph, \
             patch('agents.graph_builder.get_vector_service') as mock_vec:
            mock_llm.return_value = MagicMock()

            mock_graph_instance = MagicMock()
            mock_graph_instance.is_connected = True
            mock_graph.return_value = mock_graph_instance

            mock_vec_instance = MagicMock()
            mock_vec_instance.is_connected = False
            mock_vec.return_value = mock_vec_instance

            yield GraphBuilderAgent()

    def test_seed_jobs_count(self, builder):
        """测试种子数据数量"""
        seed_jobs = builder._get_seed_jobs()
        assert len(seed_jobs) >= 20

    def test_seed_jobs_domains(self, builder):
        """测试种子数据覆盖领域"""
        seed_jobs = builder._get_seed_jobs()
        domains = set(j["domain"] for j in seed_jobs)
        assert "人工智能" in domains
        assert "大数据" in domains
        assert "云计算" in domains
        assert "软件开发" in domains

    def test_seed_jobs_skills(self, builder):
        """测试种子岗位的技能要求"""
        seed_jobs = builder._get_seed_jobs()
        for job in seed_jobs:
            assert "job_title" in job
            assert "skills" in job
            assert len(job["skills"]) >= 3

    def test_build_from_empty_data(self, builder):
        """测试空数据时自动使用种子数据"""
        with patch.object(builder.graph, 'create_job_node', return_value=True), \
             patch.object(builder.graph, 'create_skill_node', return_value=True), \
             patch.object(builder.graph, 'create_requires_relation', return_value=True):
            result = builder.build_from_data([])
            assert result["jobs_updated"] > 0
            assert result["skills_added"] > 0

    def test_infer_domain(self, builder):
        """测试领域推断"""
        assert builder._infer_domain("人工智能") == "人工智能"
        assert builder._infer_domain("云计算") == "云计算"
        assert builder._infer_domain("网络安全") == "网络安全"
        assert builder._infer_domain("未知行业") == "软件开发"

    def test_infer_category(self, builder):
        """测试技能分类推断"""
        assert builder._infer_category("Spring Boot") == "框架"
        assert builder._infer_category("MySQL") == "数据库"
        assert builder._infer_category("Kubernetes") in ["云服务", "框架"]
        assert builder._infer_category("未知技能") == "其他"


if __name__ == "__main__":
    pytest.main([__file__])
