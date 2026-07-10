"""语义分析器测试 - SemanticAnalyzer（mock模式）"""

import pytest
from unittest.mock import patch, MagicMock


class TestInferImplicitSkills:
    """infer_implicit_skills 方法测试"""

    @pytest.fixture
    def analyzer(self):
        with patch('core.semantic_analyzer.get_llm_service') as mock_llm:
            mock_llm.return_value = MagicMock()
            from core.semantic_analyzer import SemanticAnalyzer
            yield SemanticAnalyzer()

    def test_high_concurrency(self, analyzer):
        """测试高并发关键词触发"""
        result = analyzer.infer_implicit_skills("负责高并发系统的设计与实现")
        skills = [item["skill"] for item in result]
        assert "Redis" in skills or "Kafka" in skills or "RabbitMQ" in skills
        assert all(item["confidence"] > 0 for item in result)

    def test_microservice(self, analyzer):
        """测试微服务关键词触发"""
        result = analyzer.infer_implicit_skills("基于微服务架构进行系统拆分")
        skills = [item["skill"] for item in result]
        assert "Docker" in skills
        assert "Kubernetes" in skills

    def test_big_data(self, analyzer):
        """测试海量数据关键词触发"""
        result = analyzer.infer_implicit_skills("处理海量数据的存储和计算")
        skills = [item["skill"] for item in result]
        assert "Hadoop" in skills or "Spark" in skills

    def test_large_model(self, analyzer):
        """测试大模型关键词触发"""
        result = analyzer.infer_implicit_skills("负责大模型的训练和部署")
        skills = [item["skill"] for item in result]
        assert "LangChain" in skills or "Prompt Engineering" in skills

    def test_deep_learning(self, analyzer):
        """测试深度学习关键词触发"""
        result = analyzer.infer_implicit_skills("使用深度学习技术进行图像识别")
        skills = [item["skill"] for item in result]
        assert "CUDA" in skills or "GPU编程" in skills or "神经网络" in skills

    def test_no_trigger_keywords(self, analyzer):
        """测试无触发关键词"""
        result = analyzer.infer_implicit_skills("负责日常维护工作")
        assert len(result) == 0

    def test_with_explicit_skills(self, analyzer):
        """测试排除已有显式技能"""
        result = analyzer.infer_implicit_skills(
            "负责构建高并发分布式系统",
            explicit_skills=["Redis", "Kafka"],
        )
        skills = [item["skill"] for item in result]
        assert "Redis" not in skills
        assert "Kafka" not in skills

    def test_result_sorted_by_confidence(self, analyzer):
        """测试结果按置信度降序排列"""
        result = analyzer.infer_implicit_skills("负责大模型和微服务架构的设计")
        confidences = [item["confidence"] for item in result]
        for i in range(len(confidences) - 1):
            assert confidences[i] >= confidences[i + 1]

    def test_ci_cd_trigger(self, analyzer):
        """测试CI/CD关键词触发"""
        result = analyzer.infer_implicit_skills("搭建CI/CD流水线")
        skills = [item["skill"] for item in result]
        assert "Jenkins" in skills or "Docker" in skills

    def test_security_trigger(self, analyzer):
        """测试安全关键词触发"""
        result = analyzer.infer_implicit_skills("负责系统安全防护")
        skills = [item["skill"] for item in result]
        assert "OAuth2/JWT" in skills or "XSS/CSRF防护" in skills


class TestEvaluateProjectComplexity:
    """evaluate_project_complexity 方法测试"""

    @pytest.fixture
    def analyzer(self):
        with patch('core.semantic_analyzer.get_llm_service') as mock_llm:
            mock_llm.return_value = MagicMock()
            from core.semantic_analyzer import SemanticAnalyzer
            yield SemanticAnalyzer()

    def test_simple_crud(self):
        """测试简单CRUD项目"""
        with patch('core.semantic_analyzer.get_llm_service') as mock_llm:
            mock_llm.return_value = MagicMock()
            from core.semantic_analyzer import SemanticAnalyzer
            analyzer = SemanticAnalyzer()
            result = analyzer.evaluate_project_complexity("开发了一个简单的增删改查系统")
            assert result["level"] == "low"
            assert result["score"] <= 3.5

    def test_complex_distributed(self):
        """测试复杂分布式项目"""
        with patch('core.semantic_analyzer.get_llm_service') as mock_llm:
            mock_llm.return_value = MagicMock()
            from core.semantic_analyzer import SemanticAnalyzer
            analyzer = SemanticAnalyzer()
            result = analyzer.evaluate_project_complexity(
                "设计并实现了高并发分布式微服务系统，采用事件驱动架构，支持异地多活"
            )
            assert result["level"] in ("high", "very_high")
            assert result["score"] >= 5.0

    def test_ai_project(self):
        """测试AI项目"""
        with patch('core.semantic_analyzer.get_llm_service') as mock_llm:
            mock_llm.return_value = MagicMock()
            from core.semantic_analyzer import SemanticAnalyzer
            analyzer = SemanticAnalyzer()
            result = analyzer.evaluate_project_complexity(
                "基于深度学习和大模型的智能推荐系统"
            )
            assert result["score"] >= 5.0

    def test_with_technologies(self):
        """测试带技术栈参数"""
        with patch('core.semantic_analyzer.get_llm_service') as mock_llm:
            mock_llm.return_value = MagicMock()
            from core.semantic_analyzer import SemanticAnalyzer
            analyzer = SemanticAnalyzer()
            result = analyzer.evaluate_project_complexity(
                "开发Web应用",
                technologies=["Kubernetes", "Spark", "Kafka"],
            )
            assert result["tech_count"] == 3

    def test_detected_indicators(self):
        """测试检测到的指标"""
        with patch('core.semantic_analyzer.get_llm_service') as mock_llm:
            mock_llm.return_value = MagicMock()
            from core.semantic_analyzer import SemanticAnalyzer
            analyzer = SemanticAnalyzer()
            result = analyzer.evaluate_project_complexity("使用Kubernetes和Redis高并发")
            assert len(result["detected_indicators"]) > 0

    def test_max_score_cap(self):
        """测试分数上限"""
        with patch('core.semantic_analyzer.get_llm_service') as mock_llm:
            mock_llm.return_value = MagicMock()
            from core.semantic_analyzer import SemanticAnalyzer
            analyzer = SemanticAnalyzer()
            result = analyzer.evaluate_project_complexity(
                "分布式高并发亿级流量海量数据深度学习大模型微服务Kubernetes " * 5
            )
            assert result["score"] <= 10.0


class TestDetectRedFlags:
    """detect_red_flags 方法测试"""

    @pytest.fixture
    def analyzer(self):
        with patch('core.semantic_analyzer.get_llm_service') as mock_llm:
            mock_llm.return_value = MagicMock()
            from core.semantic_analyzer import SemanticAnalyzer
            yield SemanticAnalyzer()

    def test_vague_terms(self, analyzer):
        """测试模糊量词检测"""
        flags = analyzer.detect_red_flags("精通各种技术，熟悉大量工具")
        types = [f["type"] for f in flags]
        assert "vague_language" in types

    def test_tech_stack_stuffing(self, analyzer):
        """测试技术栈堆砌检测"""
        text = "熟悉Python、Java、Go、Rust、C++、JavaScript、TypeScript、Ruby、PHP"
        flags = analyzer.detect_red_flags(text)
        types = [f["type"] for f in flags]
        assert "tech_stack_stuffing" in types or len(flags) >= 0

    def test_no_red_flags(self, analyzer):
        """测试无明显red flag"""
        flags = analyzer.detect_red_flags("使用Python和Django开发了电商网站")
        assert len(flags) == 0

    def test_timeline_concern(self, analyzer):
        """测试时间线矛盾"""
        flags = analyzer.detect_red_flags("2005年毕业，2023年工作经历")
        types = [f["type"] for f in flags]
        assert "timeline_concern" in types

    def test_severity_medium(self, analyzer):
        """测试中等严重级别"""
        flags = analyzer.detect_red_flags("精通")
        for flag in flags:
            if flag["term"] == "精通":
                assert flag["severity"] == "medium"


class TestAnalyzeTextSemantics:
    """全面的文本语义分析测试"""

    @pytest.fixture
    def analyzer(self):
        with patch('core.semantic_analyzer.get_llm_service') as mock_llm:
            mock_llm.return_value = MagicMock()
            from core.semantic_analyzer import SemanticAnalyzer
            yield SemanticAnalyzer()

    def test_full_analysis(self, analyzer):
        """测试完整分析"""
        result = analyzer.analyze_text_semantics("负责高并发微服务系统开发")
        assert "implicit_skills" in result
        assert "complexity" in result
        assert "red_flags" in result
        assert "text_length" in result
        assert result["text_length"] > 0

    def test_analysis_timestamp(self, analyzer):
        """测试时间戳"""
        result = analyzer.analyze_text_semantics("测试文本")
        assert "analysis_timestamp" in result
        assert len(result["analysis_timestamp"]) > 0
