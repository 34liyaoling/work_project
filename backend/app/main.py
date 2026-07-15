"""FastAPI 主入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.neo4j_db import neo4j_client
from app.core.es_client import es_client
from app.core.logger import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动初始化 + 关闭清理"""
    log.info(f"启动 {settings.APP_NAME} (env={settings.APP_ENV})")
    # 初始化
    try:
        init_db()
    except Exception as e:
        log.warning(f"MySQL 初始化跳过（数据库可能未启动）: {e}")
    try:
        neo4j_client.init_schema()
    except Exception as e:
        log.warning(f"Neo4j Schema 初始化跳过: {e}")
    try:
        es_client.init_indices()
    except Exception as e:
        log.warning(f"Elasticsearch 索引初始化跳过: {e}")
    yield
    # 关闭
    neo4j_client.close()
    log.info(f"{settings.APP_NAME} 关闭")


app = FastAPI(
    title=settings.APP_NAME,
    description="多源异构数据驱动岗位和能力图谱构建与动态演化分析系统",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health():
    """健康检查"""
    return {
        "mysql": True,  # 简化处理
        "neo4j": neo4j_client._driver is not None,
        "elasticsearch": es_client.client is not None
    }


# 注册 API 路由
from app.api import jd, resume, graph, match, crawl, role, health  # noqa: E402
app.include_router(jd.router, prefix="/api/jd", tags=["JD管理"])
app.include_router(resume.router, prefix="/api/resume", tags=["简历解析"])
app.include_router(graph.router, prefix="/api/graph", tags=["图谱查询"])
app.include_router(match.router, prefix="/api/match", tags=["人岗匹配"])
app.include_router(crawl.router, prefix="/api/crawl", tags=["数据采集"])
app.include_router(role.router, prefix="/api/role", tags=["岗位管理"])
app.include_router(health.router, prefix="/api", tags=["健康检查"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
