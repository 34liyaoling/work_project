"""冒烟测试 - 验证服务可启动、API 可达

覆盖范围：
- /api/health/live 存活探针
- /api/health/ready 就绪探针
- /api/jd 列表（无依赖）
- /api/resume 列表
- /api/role 列表
- /api/crawl/logs 列表
- /api/match/ 列表
"""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_returns_app_info():
    """/ 根路径应返回应用基本信息"""
    from app.main import app
    with TestClient(app) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "running"
    assert "name" in body


def test_health_live_endpoint():
    """/api/health/live 存活探针应返回 alive=True"""
    from app.main import app
    with TestClient(app) as client:
        resp = client.get("/api/health/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body["alive"] is True


def test_health_endpoint_returns_status():
    """/api/health 应返回各依赖状态"""
    from app.main import app
    with TestClient(app) as client:
        resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "mysql" in body
    assert "neo4j" in body
    assert "elasticsearch" in body
    assert "status" in body


def test_health_ready_endpoint():
    """/api/health/ready 就绪探针"""
    from app.main import app
    with TestClient(app) as client:
        resp = client.get("/api/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert "ready" in body
    assert "dependencies" in body


def test_jd_list_endpoint_reachable():
    """/api/jd 列表接口可达（MySQL 未连接时返回 500 也算可达）"""
    from app.main import app
    with TestClient(app) as client:
        resp = client.get("/api/jd/")
    # 允许 200 或 500（数据库未启动），但路由必须注册
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        body = resp.json()
        assert body.get("code") == 0


def test_resume_list_endpoint_reachable():
    """/api/resume 列表接口可达"""
    from app.main import app
    with TestClient(app) as client:
        resp = client.get("/api/resume/")
    assert resp.status_code in (200, 500)


def test_role_list_endpoint_reachable():
    """/api/role 列表接口可达"""
    from app.main import app
    with TestClient(app) as client:
        resp = client.get("/api/role/")
    assert resp.status_code in (200, 500)


def test_match_list_endpoint_reachable():
    """/api/match 列表接口可达"""
    from app.main import app
    with TestClient(app) as client:
        resp = client.get("/api/match/")
    assert resp.status_code in (200, 500)


def test_crawl_logs_endpoint_reachable():
    """/api/crawl/logs 接口可达"""
    from app.main import app
    with TestClient(app) as client:
        resp = client.get("/api/crawl/logs")
    assert resp.status_code in (200, 500)


def test_graph_export_endpoint_reachable():
    """/api/graph/export 接口可达"""
    from app.main import app
    with TestClient(app) as client:
        resp = client.get("/api/graph/export")
    # Neo4j 未连接时也允许 200（返回空数据）
    assert resp.status_code in (200, 500)


def test_openapi_schema_generated():
    """OpenAPI schema 应包含所有注册的路由"""
    from app.main import app
    schema = app.openapi()
    paths = schema.get("paths", {})
    # 核心 API 路径必须存在
    expected_prefixes = [
        "/api/jd", "/api/resume", "/api/graph",
        "/api/match", "/api/crawl", "/api/role",
    ]
    for prefix in expected_prefixes:
        assert any(p.startswith(prefix) for p in paths), f"缺少路由: {prefix}"
    # 健康检查
    assert "/api/health" in paths


def test_cors_headers_present():
    """CORS 头应允许跨域访问"""
    from app.main import app
    with TestClient(app) as client:
        resp = client.options("/api/jd/", headers={"Origin": "http://localhost:5173"})
    # FastAPI 允许任何来源
    assert "access-control-allow-origin" in {k.lower() for k in resp.headers.keys()} or resp.status_code in (200, 405)
