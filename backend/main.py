"""FastAPI 后端服务主入口"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("=== 新一代信息技术全景图谱系统 - API服务启动 ===")

    # 启动时初始化
    try:
        from core.vector_service import get_vector_service
        vector = get_vector_service()
        vector.connect()
        logger.info("向量数据库连接成功")
    except Exception as e:
        logger.warning(f"向量数据库初始化跳过: {e}")

    yield

    logger.info("=== API服务关闭 ===")


app = FastAPI(
    title="新一代信息技术全景图谱系统 API",
    description="""
## 全流程闭环系统 API 接口文档

### 核心功能模块
1. **多源数据采集** → 数据清洗 → 交叉验证
2. **新岗位发现** → 能力定义 → 审核入库
3. **动态知识图谱** → 构建/更新/查询
4. **简历深度解析** → 语义理解 → 可信度评估
5. **精准智能匹配** → 差距分析 → 学习路径规划

### 技术创新点
- 时序动态知识图谱 (TD-KG)
- 多源交叉验证引擎 (MSVE)
- 幻觉防控四层防御体系 (HPF)
- 多智能体协作架构 (Multi-Agent via CrewAI)
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
from backend.api.routes import data, graph, resume, matching, jobs, qa, career, batch, system, orchestrate

app.include_router(data.router)
app.include_router(graph.router)
app.include_router(resume.router)
app.include_router(matching.router)
app.include_router(jobs.router)
app.include_router(qa.router)
app.include_router(career.router)
app.include_router(batch.router)
app.include_router(system.router)
app.include_router(orchestrate.router)

# 挂载前端静态文件（必须在API路由之后）
from fastapi.staticfiles import StaticFiles
from pathlib import Path
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    logger.info(f"前端静态文件已挂载: {frontend_dist}")

    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("health") or full_path == "docs" or full_path.startswith("openapi"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"error": "frontend not built"}
else:
    logger.warning("前端dist目录不存在，请先构建前端")


@app.get("/")
async def root():
    return {
        "service": "新一代信息技术全景图谱系统",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "timestamp": __import__('datetime').datetime.now().isoformat()}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc), "detail": type(exc).__name__},
    )


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
