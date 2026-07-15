# CompetencyGraph

> **XH-202621 赛题**：多源异构数据驱动岗位和能力图谱构建与动态演化分析
> 发榜方：科大讯飞

## 项目简介

CompetencyGraph 是一个面向招聘领域的数据智能平台，旨在从拉勾、Boss直聘、猎聘、LinkedIn 等多源数据中：

1. **采集** JD 与简历
2. **解析** 出结构化的技能、责任、经验等
3. **构建** 岗位与技能的关系图谱
4. **演化** 跟踪技能与岗位定义的动态变化
5. **匹配** 人岗（具体 JD / 岗位方向 Top-N）
6. **发现** 新岗位与既有岗位更新

## 技术栈

### 后端
- **Web 框架**：FastAPI 0.115
- **数据库**：MySQL 8（关系数据）、Neo4j 5（图谱）、Elasticsearch 8（搜索/向量）
- **ORM**：SQLAlchemy 2.0
- **LLM**：讯飞星火 4.0 Ultra
- **文档解析**：PyMuPDF、python-docx
- **缓存**：内置内存缓存（Redis 风格 API）
- **测试**：pytest + pytest-cov（覆盖率 ≥ 60%）

### 前端
- **框架**：Vue 3 + Composition API + `<script setup>`
- **构建**：Vite 5
- **状态**：Pinia 2
- **UI**：Element Plus
- **图谱**：AntV G6 5
- **图表**：ECharts 5
- **HTTP**：Axios

## 目录结构

```
competency-graph/
├── backend/                # 后端（FastAPI）
│   ├── app/
│   │   ├── api/            # 路由：jd/resume/graph/match/crawl/role/health
│   │   ├── core/           # config/database/neo4j_db/es_client/cache/logger
│   │   ├── models/         # ORM 模型
│   │   ├── services/       # 业务服务（crawler/llm/monitor/...）
│   │   ├── e2e/            # 端到端流水线
│   │   └── main.py
│   ├── scripts/            # init_db.sql / init_neo4j.cypher
│   ├── tests/              # 单元/冒烟测试
│   ├── data/               # 技能词典等
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # 前端（Vue 3）
│   ├── src/
│   │   ├── api/            # axios 封装 + 各模块 API
│   │   ├── components/     # 业务组件
│   │   ├── stores/         # Pinia 状态
│   │   ├── views/          # 三大页面
│   │   ├── router/         # 路由
│   │   ├── styles/         # 全局样式
│   │   ├── utils/          # request/format
│   │   ├── App.vue
│   │   └── main.js
│   ├── public/             # favicon
│   ├── Dockerfile
│   └── nginx.conf
├── docs/                   # 项目文档
│   ├── DEPLOYMENT.md
│   └── API.md
├── docker-compose.yml      # 全栈一键编排
└── README.md
```

## 快速开始

### 方式一：Docker 一键启动（全栈）

```bash
cd competency-graph
docker compose up -d
```

- 前端：<http://localhost:8080>
- 后端 API：<http://localhost:8000>
- API 文档：<http://localhost:8000/docs>
- Neo4j Browser：<http://localhost:7474>
- Kibana（ES）：<http://localhost:9200>

### 方式二：本地开发模式

#### 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
# 修改 .env 中的 MySQL/Neo4j/ES 连接信息
uvicorn app.main:app --reload --port 8000
```

#### 前端

```bash
cd frontend
npm install
npm run dev
# 浏览器访问 http://localhost:5173
```

## 核心功能页面

### 1. 全景图谱可视化（`/graph`）
- AntV G6 渲染技能级粒度交互图谱
- 多视图切换：默认 / 技术栈 / 级别 / 领域
- 节点点击 → 技能变化时间线
- 搜索过滤 + 缩放/拖拽

### 2. 人岗匹配诊断（`/match`）
- **模式一**：与具体 JD 匹配（精准）
- **模式二**：与岗位方向 Top-N 排名（探索）
- 总体匹配率仪表盘 + 分维度评分
- 技能差距分析（按重要性颜色标注）
- 学习路径与改进建议

### 3. 岗位管理（`/role`）
- 新岗位发现列表（带置信度）
- 既有岗位更新列表
- 人工审核队列
- 一键触发岗位发现

## 测试

```bash
cd backend
pytest                         # 全部测试
pytest --cov=app --cov-report=html  # 覆盖率报告
pytest tests/test_smoke.py -v  # 冒烟测试
pytest tests/test_matching.py -v   # 匹配测试
pytest tests/test_skill_normalizer.py -v  # 技能标准化测试
```

## 文档

- [部署文档](docs/DEPLOYMENT.md)
- [API 文档](docs/API.md)

## 性能指标

- 90% JD 解析准确率
- 90% 简历解析准确率
- 90% 双方式人岗匹配准确率
- 端到端流水线吞吐：> 100 JD/分钟

## License

仅供 XH-202621 赛题使用。
