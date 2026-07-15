# =============================================================
# CompetencyGraph 后端 Docker 镜像
# 多阶段构建：先装依赖，再用精简运行时
# =============================================================

# ---- 阶段 1：构建依赖 ----
FROM python:3.11-slim AS builder

WORKDIR /app

# 系统依赖（构建 PyMuPDF 等 C 扩展）
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 使用清华源加速
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
        --prefix=/install \
        -r requirements.txt

# ---- 阶段 2：运行时 ----
FROM python:3.11-slim

WORKDIR /app

# 运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
        default-libmysqlclient-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 复制已安装的包
COPY --from=builder /install /usr/local

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p ./data/resumes ./logs

# 环境变量默认值
ENV APP_ENV=production \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/live || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
