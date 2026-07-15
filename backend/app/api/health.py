"""健康检查 API

提供细粒度的服务健康状态查询。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.es_client import es_client
from app.core.logger import log
from app.core.neo4j_db import neo4j_client

router = APIRouter()


def _check_mysql() -> bool:
    """检查 MySQL 可用性"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        log.warning(f"MySQL 健康检查失败: {e}")
        return False


def _check_neo4j() -> bool:
    """检查 Neo4j 可用性"""
    try:
        session = neo4j_client.get_session()
        if not session:
            return False
        try:
            session.run("RETURN 1")
            return True
        finally:
            session.close()
    except Exception as e:
        log.warning(f"Neo4j 健康检查失败: {e}")
        return False


def _check_elasticsearch() -> bool:
    """检查 Elasticsearch 可用性"""
    try:
        return bool(es_client.client and es_client.client.ping())
    except Exception as e:
        log.warning(f"ES 健康检查失败: {e}")
        return False


@router.get("/health", summary="基础健康检查")
def health():
    """返回各依赖服务的可用性"""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "env": settings.APP_ENV,
        "mysql": _check_mysql(),
        "neo4j": _check_neo4j(),
        "elasticsearch": _check_elasticsearch(),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/health/ready", summary="就绪探针")
def ready():
    """K8s/Docker 就绪探针：所有关键依赖正常才返回 200"""
    deps = {
        "mysql": _check_mysql(),
        "neo4j": _check_neo4j(),
        "elasticsearch": _check_elasticsearch(),
    }
    all_ok = all(deps.values())
    return {
        "ready": all_ok,
        "dependencies": deps,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/health/live", summary="存活探针")
def live():
    """K8s/Docker 存活探针：进程存活即视为通过"""
    return {
        "alive": True,
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }
