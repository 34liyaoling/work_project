# 部署文档（DEPLOYMENT）

> XH-202621 赛题 · CompetencyGraph 部署手册
>
> 涵盖：环境准备、依赖安装、本地启动、Docker 部署、常见问题。

## 一、环境要求

### 1.1 基础环境

| 组件     | 版本          | 说明                       |
|----------|---------------|----------------------------|
| Python   | 3.11+         | 后端运行时                 |
| Node.js  | 20+           | 前端构建                   |
| Docker   | 24+           | 容器化部署（可选）         |
| MySQL    | 8.0+          | 关系数据                   |
| Neo4j    | 5.x           | 图数据库                   |
| Elasticsearch | 8.x       | 全文/向量检索              |

### 1.2 硬件最低配置

- CPU：4 核
- 内存：8 GB（生产建议 16 GB+）
- 磁盘：20 GB+（含 Neo4j / ES 索引）

## 二、本地开发部署

### 2.1 启动依赖服务

#### MySQL

```bash
# Windows / macOS / Linux
docker run -d --name cg_mysql -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=competency_graph \
  -v $(pwd)/backend/scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql:ro \
  mysql:8.0 --default-authentication-plugin=mysql_native_password
```

#### Neo4j

```bash
docker run -d --name cg_neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/neo4j123 \
  -v neo4j_data:/data \
  neo4j:5.20-community
```

#### Elasticsearch

```bash
docker run -d --name cg_es -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "ES_JAVA_OPTS=-Xms1g -Xmx1g" \
  docker.elastic.co/elasticsearch/elasticsearch:8.13.4
```

### 2.2 初始化数据库

```bash
# 1) MySQL：执行 init_db.sql
mysql -h127.0.0.1 -uroot -proot < backend/scripts/init_db.sql

# 2) Neo4j：执行 init_neo4j.cypher
# 浏览器访问 http://localhost:7474 ，粘贴 cypher 内容并执行
# 或使用 cypher-shell：
cat backend/scripts/init_neo4j.cypher | docker exec -i cg_neo4j cypher-shell -u neo4j -p neo4j123
```

### 2.3 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env：填入 MySQL/Neo4j/ES 真实地址

# 启动开发服务器
uvicorn app.main:app --reload --port 8000

# 验证
curl http://localhost:8000/api/health
```

### 2.4 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev
# 访问 http://localhost:5173

# 生产构建
npm run build
npm run preview
```

## 三、Docker 全栈部署

### 3.1 一键启动

```bash
cd competency-graph

# 构建并启动
docker compose up -d

# 查看日志
docker compose logs -f backend

# 验证
curl http://localhost:8000/api/health
```

### 3.2 服务端口

| 服务       | 端口  | 访问地址                          |
|------------|-------|-----------------------------------|
| 前端       | 8080  | <http://localhost:8080>           |
| 后端       | 8000  | <http://localhost:8000>           |
| API 文档   | 8000  | <http://localhost:8000/docs>      |
| Neo4j UI   | 7474  | <http://localhost:7474>           |
| Neo4j Bolt | 7687  | bolt://localhost:7687             |
| ES         | 9200  | <http://localhost:9200>           |
| MySQL      | 3306  | localhost:3306（root/root）       |

### 3.3 停止与清理

```bash
# 停止
docker compose down

# 停止并删除数据卷
docker compose down -v
```

## 四、生产环境建议

### 4.1 安全

- 修改所有默认密码（MySQL/Neo4j）
- 关闭 CORS `allow_origins=["*"]`，按需限定
- 启用 HTTPS（Nginx + Let's Encrypt）
- 讯飞星火 API Key 放入 `.env`，**不要提交到 Git**

### 4.2 性能调优

- MySQL `innodb_buffer_pool_size` ≥ 4 GB
- Neo4j `dbms.memory.heap.max_size` ≥ 4 GB
- ES `ES_JAVA_OPTS=-Xms4g -Xmx4g`
- 后端 workers 数量 = CPU * 2 + 1

### 4.3 监控

- 后端：`/api/health/ready` 作为 K8s/Docker 健康探针
- 缓存状态：通过 `app.core.cache.get_cache_snapshot()` 监控命中率
- 日志：查看 `backend/logs/app_*.log`

## 五、常见问题

### Q1：MySQL 报错 "Can't connect to MySQL server"
A：检查 `.env` 中 `MYSQL_HOST/PORT` 是否正确；防火墙是否放行 3306。

### Q2：Neo4j 启动失败 "Memory setting invalid"
A：宿主机内存不足，需调整 `NEO4J_dbms_memory_heap_max__size`（建议 ≤ 宿主机内存的 1/2）。

### Q3：前端跨域
A：开发模式已通过 Vite 代理解决；生产模式通过 Nginx `proxy_pass` 转发。

### Q4：上传 PDF 简历解析失败
A：检查 `pip install PyMuPDF` 是否成功；可在 `data/resumes/` 中查看文件是否落盘。

### Q5：测试覆盖率不足 60%
A：运行 `pytest --cov=app --cov-report=term-missing` 查看未覆盖行，针对性补测。

## 六、目录速查

```
backend/
├── .env.example          # 环境变量模板
├── requirements.txt      # Python 依赖
├── pytest.ini            # 测试配置
├── Dockerfile            # 后端镜像
├── docker-compose.yml    # 仅后端编排
├── scripts/
│   ├── init_db.sql       # MySQL 初始化
│   └── init_neo4j.cypher # Neo4j 初始化
├── data/
│   ├── skill_dictionary.json  # 技能同义词
│   └── resumes/              # 上传的简历文件
└── tests/
    ├── conftest.py
    ├── test_smoke.py
    ├── test_matching.py
    └── test_skill_normalizer.py
```

## 七、版本升级

```bash
# 拉取最新代码
git pull

# 后端：重装依赖
cd backend && pip install -r requirements.txt

# 前端：重装依赖
cd ../frontend && npm install

# 重新部署
cd .. && docker compose up -d --build
```
