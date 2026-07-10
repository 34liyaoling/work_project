import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

from models.job_model import JobPostRaw, JobPostSource
from models.resume_model import CredibilityLevel, SkillWithCredibility
from models.graph_nodes import SkillNode, SkillCategory, SkillDomain, LifecycleStage


@pytest.fixture
def sample_resume_profile():
    return {
        "name": "张三",
        "skills": ["Python", "PyTorch", "机器学习", "深度学习", "SQL", "Docker"],
        "skills_with_credibility": [
            {"skill_name": "Python", "credibility_score": 0.9},
            {"skill_name": "PyTorch", "credibility_score": 0.85},
            {"skill_name": "机器学习", "credibility_score": 0.8},
            {"skill_name": "深度学习", "credibility_score": 0.75},
            {"skill_name": "SQL", "credibility_score": 0.7},
            {"skill_name": "Docker", "credibility_score": 0.65},
        ],
        "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
        "implicit_skills": ["NLP", "数据分析", "分布式系统"],
        "overall_technical_level": "senior",
    }


@pytest.fixture
def sample_job_requirement():
    return {
        "title": "AI算法工程师",
        "required_skills": ["Python", "PyTorch", "机器学习", "TensorFlow"],
        "optional_skills": ["SQL", "Docker", "Kubernetes"],
        "embedding": [0.15, 0.25, 0.35, 0.45, 0.55],
    }


@pytest.fixture
def sample_job_post_raw():
    now = datetime.now()
    return JobPostRaw(
        source=JobPostSource.BOSS_ZHIPIN,
        source_confidence=0.8,
        timestamp=now,
        raw_content='{"jobTitle": "AI工程师", "skills": ["Python", "PyTorch"]}',
        job_title="AI工程师",
        company_name="字节跳动",
        skills=["Python", "PyTorch", "机器学习"],
        salary_min=30,
        salary_max=80,
        location="北京",
        experience_min=3,
        experience_max=5,
        education="硕士",
        completeness_score=0.85,
        freshness_score=0.9,
    )


@pytest.fixture
def mock_graph_service():
    mock = MagicMock()
    mock.is_connected = False
    mock.execute_query.return_value = []
    mock.find_path_between_skills.return_value = []
    mock.create_job_node.return_value = True
    mock.create_skill_node.return_value = True
    mock.create_requires_relation.return_value = True
    return mock


@pytest.fixture
def mock_llm_service():
    mock = MagicMock()
    mock.structured_extraction.return_value = []
    return mock


@pytest.fixture
def mock_vector_service():
    mock = MagicMock()
    mock.is_connected = False
    return mock
