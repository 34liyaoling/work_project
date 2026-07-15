# =============================================================
# CompetencyGraph 前端 Docker 镜像
# 多阶段构建：Node 构建静态文件 + Nginx 提供服务
# =============================================================

# ---- 阶段 1：构建 ----
FROM node:20-alpine AS builder

WORKDIR /app

# 淘宝镜像加速
RUN npm config set registry https://registry.npmmirror.com

COPY package*.json ./
RUN npm install --no-audit --no-fund

COPY . .
RUN npm run build

# ---- 阶段 2：Nginx ----
FROM nginx:1.25-alpine

# 复制自定义配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
