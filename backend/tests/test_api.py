"""API 集成测试 - 关键端点 200 状态码验证"""
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """构建 FastAPI 测试客户端，对外部依赖做最小 mock"""
    with patch("app.core.database.init_db", lambda: None), \
         patch("app.core.neo4j_db.neo4j_client._connect", lambda: None), \
         patch("app.core.es_client.es_client.init_indices", lambda: None):
        from app.main import app
        return TestClient(app)


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "name" in body
    assert body["status"] == "running"


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_jd_list(client):
    r = client.get("/api/jd/")
    assert r.status_code in (200, 204)


def test_resume_list(client):
    r = client.get("/api/resume/")
    assert r.status_code in (200, 204)


def test_graph_list(client):
    r = client.get("/api/graph/")
    assert r.status_code in (200, 204)


def test_match_list(client):
    r = client.get("/api/match/")
    assert r.status_code in (200, 204)


def test_crawl_list(client):
    r = client.get("/api/crawl/")
    assert r.status_code in (200, 204)


def test_role_list(client):
    r = client.get("/api/role/")
    assert r.status_code in (200, 204)
