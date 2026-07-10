"""匹配引擎测试 - HybridMatchEngine（mock模式）"""

import pytest
from unittest.mock import patch, MagicMock

from core.match_engine import HybridMatchEngine, MatchResult


class TestMatchResult:
    """MatchResult 对象测试"""

    def test_create(self):
        """测试 MatchResult 创建"""
        result = MatchResult(
            score=0.85,
            job_title="AI工程师",
            breakdown={"skill": 0.9, "graph": 0.7},
            matched_skills=["Python", "PyTorch"],
            missing_critical=["TensorFlow"],
            missing_optional=["Kubernetes"],
            explanation="匹配度较高",
        )
        assert result.score == 0.85
        assert result.job_title == "AI工程师"
        assert result.explanation == "匹配度较高"
        assert len(result.matched_skills) == 2

    def test_score_range(self):
        """测试分数范围"""
        result = MatchResult(
            score=0.0,
            job_title="零匹配",
            breakdown={},
            matched_skills=[],
            missing_critical=[],
            missing_optional=[],
        )
        assert result.score == 0.0

    def test_default_explanation(self):
        """测试默认 explanation"""
        result = MatchResult(
            score=0.5,
            job_title="默认测试",
            breakdown={},
            matched_skills=[],
            missing_critical=[],
            missing_optional=[],
        )
        assert result.explanation == ""


class TestHybridMatchEngine:
    """HybridMatchEngine 核心功能测试"""

    @pytest.fixture
    def engine(self):
        with patch('core.match_engine.get_llm_service') as mock_llm, \
             patch('core.match_engine.get_graph_service') as mock_graph, \
             patch('core.match_engine.get_vector_service') as mock_vec:
            mock_graph_instance = MagicMock()
            mock_graph_instance.is_connected = False
            mock_graph.return_value = mock_graph_instance

            mock_vec_instance = MagicMock()
            mock_vec_instance.is_connected = False
            mock_vec.return_value = mock_vec_instance

            yield HybridMatchEngine()

    def test_default_weights(self, engine):
        """测试默认权重"""
        assert engine.weights["skill"] == 0.35
        assert engine.weights["graph"] == 0.20
        assert engine.weights["vector"] == 0.25
        assert engine.weights["trend"] == 0.10
        assert engine.weights["credibility"] == 0.10
        assert sum(engine.weights.values()) == 1.0

    def test_custom_weights(self):
        """测试自定义权重"""
        custom = {"skill": 0.5, "graph": 0.1, "vector": 0.2, "trend": 0.1, "credibility": 0.1}
        with patch('core.match_engine.get_llm_service'), \
             patch('core.match_engine.get_graph_service'), \
             patch('core.match_engine.get_vector_service'):
            engine = HybridMatchEngine(custom_weights=custom)
            assert engine.weights["skill"] == 0.5


class TestCalculateMatch:
    """calculate_match 方法测试"""

    @pytest.fixture
    def engine(self):
        with patch('core.match_engine.get_llm_service') as mock_llm, \
             patch('core.match_engine.get_graph_service') as mock_graph, \
             patch('core.match_engine.get_vector_service') as mock_vec:
            mock_graph_instance = MagicMock()
            mock_graph_instance.is_connected = False
            mock_graph.return_value = mock_graph_instance

            mock_vec_instance = MagicMock()
            mock_vec_instance.is_connected = False
            mock_vec.return_value = mock_vec_instance

            yield HybridMatchEngine()

    def test_full_match(self, engine):
        """测试完全匹配"""
        resume = {
            "skills": ["Python", "PyTorch", "机器学习", "深度学习", "SQL"],
            "skills_with_credibility": [
                {"skill_name": "Python", "credibility_score": 0.9},
                {"skill_name": "PyTorch", "credibility_score": 0.85},
                {"skill_name": "机器学习", "credibility_score": 0.8},
            ],
            "embedding": [0.1, 0.2, 0.3],
            "implicit_skills": ["NLP", "数据分析"],
        }
        job = {
            "title": "AI算法工程师",
            "required_skills": ["Python", "PyTorch", "机器学习", "TensorFlow"],
            "optional_skills": ["SQL", "Docker"],
            "embedding": [0.15, 0.25, 0.35],
        }

        result = engine.calculate_match(resume, job)
        assert isinstance(result, MatchResult)
        assert 0 <= result.score <= 1.0
        assert len(result.matched_skills) > 0
        assert "Python" in result.matched_skills
        assert result.job_title == "AI算法工程师"

    def test_no_match(self, engine):
        """测试完全不匹配"""
        resume = {
            "skills": ["烹饪", "摄影"],
            "skills_with_credibility": [],
            "embedding": None,
            "implicit_skills": [],
        }
        job = {
            "title": "AI算法工程师",
            "required_skills": ["Python", "PyTorch", "机器学习"],
            "optional_skills": [],
            "embedding": None,
        }

        result = engine.calculate_match(resume, job)
        assert result.score >= 0
        assert len(result.matched_skills) == 0
        assert len(result.missing_critical) == 3

    def test_partial_match(self, engine):
        """测试部分匹配"""
        resume = {
            "skills": ["Python", "SQL"],
            "skills_with_credibility": [
                {"skill_name": "Python", "credibility_score": 0.9},
                {"skill_name": "SQL", "credibility_score": 0.7},
            ],
            "embedding": [0.1, 0.2],
            "implicit_skills": [],
        }
        job = {
            "title": "后端工程师",
            "required_skills": ["Python", "Java", "Docker"],
            "optional_skills": ["SQL", "Redis"],
            "embedding": [0.15, 0.25],
        }

        result = engine.calculate_match(resume, job)
        assert "Python" in result.matched_skills
        assert "Java" in result.missing_critical
        assert 0 < result.score < 1.0

    def test_empty_skills(self, engine):
        """测试空技能列表"""
        resume = {
            "skills": [],
            "skills_with_credibility": [],
            "embedding": None,
            "implicit_skills": [],
        }
        job = {
            "title": "测试岗位",
            "required_skills": ["Python", "Java"],
            "optional_skills": [],
            "embedding": None,
        }

        result = engine.calculate_match(resume, job)
        assert result.score >= 0
        assert len(result.matched_skills) == 0
        assert len(result.missing_critical) == 2

    def test_five_dimension_breakdown(self, engine):
        """测试5维加权打分计算"""
        resume = {
            "skills": ["Python", "PyTorch", "机器学习", "SQL"],
            "skills_with_credibility": [
                {"skill_name": "Python", "credibility_score": 0.9},
                {"skill_name": "PyTorch", "credibility_score": 0.85},
            ],
            "embedding": [0.1, 0.2],
            "implicit_skills": [],
        }
        job = {
            "title": "ML工程师",
            "required_skills": ["Python", "PyTorch"],
            "optional_skills": ["SQL"],
            "embedding": [0.15, 0.25],
        }

        result = engine.calculate_match(resume, job)
        breakdown = result.breakdown
        expected_keys = {"skill", "graph", "vector", "trend", "credibility"}
        assert set(breakdown.keys()) == expected_keys
        for key in expected_keys:
            assert 0 <= breakdown[key] <= 1.0

    def test_skill_match_score(self, engine):
        """测试技能匹配分计算"""
        all_resume_skills = {"Python", "Java", "SQL", "React"}
        required = {"Python", "Kubernetes", "React"}
        optional = {"Docker", "SQL"}

        resume_profile = {
            "skills": list(all_resume_skills),
            "skills_with_credibility": [
                {"skill_name": "Python", "credibility_score": 0.9},
                {"skill_name": "Java", "credibility_score": 0.8},
                {"skill_name": "SQL", "credibility_score": 0.85},
                {"skill_name": "React", "credibility_score": 0.75},
            ],
        }

        score, matched, missing_crit, missing_opt = engine._calc_skill_match(
            all_resume_skills, required, optional, resume_profile
        )

        assert 0 <= score <= 1.0
        assert "Python" in matched
        assert "React" in matched
        assert "Kubernetes" in missing_crit
        assert "Docker" in missing_opt

    def test_explanation_format(self, engine):
        """测试解释文本格式"""
        explanation = engine._generate_explanation(
            "测试岗位", 0.85,
            {"skill": 0.9, "graph": 0.7, "vector": 0.8, "trend": 0.6, "credibility": 0.9},
            ["Python", "Java"], ["Go"], ["Rust"],
        )
        assert "测试岗位" in explanation
        assert "Python" in explanation
        assert "Go" in explanation


class TestBatchCalculate:
    """batch_calculate 方法测试"""

    @pytest.fixture
    def engine(self):
        with patch('core.match_engine.get_llm_service') as mock_llm, \
             patch('core.match_engine.get_graph_service') as mock_graph, \
             patch('core.match_engine.get_vector_service') as mock_vec:
            mock_graph_instance = MagicMock()
            mock_graph_instance.is_connected = False
            mock_graph.return_value = mock_graph_instance
            mock_vec_instance = MagicMock()
            mock_vec_instance.is_connected = False
            mock_vec.return_value = mock_vec_instance
            yield HybridMatchEngine()

    def test_batch_calculate(self, engine):
        """测试批量计算"""
        resume = {
            "skills": ["Python"],
            "skills_with_credibility": [{"skill_name": "Python", "credibility_score": 0.8}],
            "embedding": [0.1],
            "implicit_skills": [],
        }
        jobs = [
            {"title": "岗位A", "required_skills": ["Python"], "optional_skills": [], "embedding": [0.1]},
            {"title": "岗位B", "required_skills": ["Java"], "optional_skills": [], "embedding": [0.5]},
        ]

        results = engine.batch_calculate(resume, jobs)
        assert len(results) == 2
        assert results[0].score >= results[1].score

    def test_batch_single(self, engine):
        """测试单个批处理"""
        resume = {
            "skills": ["Python"],
            "skills_with_credibility": [{"skill_name": "Python", "credibility_score": 0.8}],
            "embedding": None,
            "implicit_skills": [],
        }
        jobs = [
            {"title": "岗位A", "required_skills": ["Python"], "optional_skills": [], "embedding": None},
        ]

        results = engine.batch_calculate(resume, jobs)
        assert len(results) == 1

    def test_batch_empty(self, engine):
        """测试空批处理"""
        resume = {
            "skills": ["Python"],
            "skills_with_credibility": [],
            "embedding": None,
            "implicit_skills": [],
        }
        results = engine.batch_calculate(resume, [])
        assert results == []


class TestFindSimilar:
    """_find_similar 方法测试"""

    @pytest.fixture
    def engine(self):
        with patch('core.match_engine.get_llm_service'), \
             patch('core.match_engine.get_graph_service'), \
             patch('core.match_engine.get_vector_service'):
            return HybridMatchEngine()

    def test_exact_case(self, engine):
        """测试精确子串匹配"""
        skill_set = {"PyTorch", "Kubernetes", "JavaScript"}
        assert engine._find_similar("pytorch", skill_set) == "PyTorch"
        assert engine._find_similar("JavaScript", skill_set) == "JavaScript"

    def test_alias_match(self, engine):
        """测试别名匹配（全小写匹配）"""
        skill_set = {"PyTorch", "Kubernetes", "JavaScript"}
        assert engine._find_similar("pytorch", skill_set) == "PyTorch"
        assert engine._find_similar("kubernetes", skill_set) == "Kubernetes"

    def test_no_match(self, engine):
        """测试无匹配"""
        skill_set = {"Python", "Java"}
        assert engine._find_similar("rust", skill_set) is None


class TestCredibilityAdjustment:
    """可信度修正测试"""

    @pytest.fixture
    def engine(self):
        with patch('core.match_engine.get_llm_service'), \
             patch('core.match_engine.get_graph_service'), \
             patch('core.match_engine.get_vector_service'):
            return HybridMatchEngine()

    def test_high_credibility(self, engine):
        """测试高可信度修正"""
        skills = [
            {"skill_name": "Python", "credibility_score": 0.9},
            {"skill_name": "Java", "credibility_score": 0.85},
        ]
        score = engine._calc_credibility_adjustment(skills)
        assert score > 0.8

    def test_low_credibility(self, engine):
        """测试低可信度修正"""
        skills = [
            {"skill_name": "Python", "credibility_score": 0.2},
        ]
        score = engine._calc_credibility_adjustment(skills)
        assert score < 0.5

    def test_empty_credibility(self, engine):
        """测试空列表"""
        score = engine._calc_credibility_adjustment([])
        assert score == 0.5
