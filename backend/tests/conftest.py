"""pytest 配置与共享 fixtures

约定：
- 默认使用 sqlite 内存库做 MySQL 替代，避免 CI 强依赖外部服务
- mock_llm 提供可预测的返回
- sample_jd / sample_resume / sample_match 提供基础测试样本
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import MagicMock

import pytest

# 让 pytest 能直接 import app.*
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


# ============================================================
# 环境变量（在导入 app 之前）
# ============================================================
@pytest.fixture(scope="session", autouse=True)
def _setup_test_env() -> None:
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("MYSQL_DATABASE", "competency_graph_test")
    # 测试时不强制连接 Neo4j/ES（具体服务按需 mock）


# ============================================================
# 数据库：默认用 sqlite 内存库
# ============================================================
@pytest.fixture(scope="session")
def engine_sqlite():
    from sqlalchemy import create_engine
    eng = create_engine("sqlite:///:memory:", future=True)
    return eng


@pytest.fixture
def db_session(engine_sqlite, monkeypatch):
    """提供隔离的 sqlite 内存库 session"""
    from sqlalchemy.orm import sessionmaker, declarative_base

    Base = declarative_base()
    # 让 app.core.database.engine 指向 sqlite，便于单测
    from app.core import database as db_mod
    monkeypatch.setattr(db_mod, "engine", engine_sqlite, raising=False)
    SessionTesting = sessionmaker(bind=engine_sqlite)
    session = SessionTesting()
    try:
        yield session
    finally:
        session.close()


# ============================================================
# LLM Mock
# ============================================================
@pytest.fixture
def mock_llm():
    """返回一个对象，提供 chat_json 返回 JSON 字符串"""
    mock = MagicMock()

    def chat_json(prompt: str, **kwargs) -> str:
        return json.dumps({
            "skills": ["Python", "SQL", "机器学习"],
            "experience_years": 3,
            "level": "中级",
        }, ensure_ascii=False)

    mock.chat_json.side_effect = chat_json
    return mock


# ============================================================
# 数据样本
# ============================================================
@pytest.fixture
def sample_jd() -> Dict[str, Any]:
    return {
        "jd_id": "JD-TEST-0001",
        "source": "lagou",
        "company": "示例公司",
        "title": "高级数据工程师",
        "category": "数据",
        "level": "高级",
        "location": "北京",
        "salary_range": "30-50K",
        "raw_text": (
            "岗位职责：\n1. 负责数据仓库建模与 ETL 流水线开发；\n"
            "2. 熟练使用 SQL/Python，熟悉 Spark/Flink；\n"
            "3. 具备 Hadoop/Hive 经验。\n\n任职要求：\n"
            "1. 5年以上数据相关经验；\n2. 熟悉 Airflow；\n"
            "3. 良好的沟通能力。"
        ),
        "published_at": "2025-04-01T00:00:00",
    }


@pytest.fixture
def sample_resume() -> Dict[str, Any]:
    return {
        "name": "张三",
        "years": 4,
        "raw_text": (
            "个人信息：张三 | 数据工程师 | 4年经验\n\n"
            "工作经历：\n- 2022-2024 XX科技 数据工程师\n"
            "  负责数仓建模，熟练使用 Python/SQL/Spark。\n\n"
            "技能：Python, SQL, Spark, Airflow, Hive"
        ),
        "skills": ["Python", "SQL", "Spark", "Airflow", "Hive"],
    }


@pytest.fixture
def sample_match() -> Dict[str, Any]:
    return {
        "resume_id": "R-TEST-0001",
        "jd_id": "JD-TEST-0001",
        "expected_match": True,
        "vector_score": 0.87,
        "graph_score": 0.82,
    }


# ============================================================
# 测试数据加载
# ============================================================
@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    return Path(__file__).resolve().parent / "test_data"


@pytest.fixture(scope="session")
def jd_corpus(test_data_dir) -> List[Dict[str, Any]]:
    p = test_data_dir / "jd_corpus.json"
    if not p.exists():
        pytest.skip(f"缺少测试数据: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def resume_corpus(test_data_dir) -> List[Dict[str, Any]]:
    p = test_data_dir / "resume_corpus.json"
    if not p.exists():
        pytest.skip(f"缺少测试数据: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def match_corpus(test_data_dir) -> List[Dict[str, Any]]:
    p = test_data_dir / "match_pairs.json"
    if not p.exists():
        pytest.skip(f"缺少测试数据: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 准确率监控 fixture
# ============================================================
@pytest.fixture
def accuracy_monitor():
    from app.services.monitor import AccuracyMonitor
    mon = AccuracyMonitor()
    yield mon
    mon.reset()
