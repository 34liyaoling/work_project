# 新一代信息技术全景图谱系统 — API 接口文档

> 基础地址：`http://localhost:8000/api/v1`
> 统一响应格式：`{ "success": bool, "message": str, "data": any, "timestamp": str }`

---

## 一、系统基础

### 1.1 健康检查

```
GET /health
```

**响应示例：**
```json
{ "status": "healthy", "timestamp": "2026-06-18T19:00:00" }
```

### 1.2 根信息

```
GET /
```

**响应示例：**
```json
{
  "service": "新一代信息技术全景图谱系统",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs"
}
```

---

## 二、数据采集模块

### 2.1 触发多源数据采集

```
POST /api/v1/data/collect
```

**请求体 (JSON)：**
```json
{
  "sources": null,
  "limit_per_source": 50,
  "force_refresh": false
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `sources` | string[] | 否 | 指定数据源，`null` 表示采集全部 |
| `limit_per_source` | int | 否 | 每源最大采集数，默认 50 |
| `force_refresh` | bool | 否 | 是否强制刷新缓存，默认 false |

**成功响应：**
```json
{
  "data": {
    "total_collected": 26,
    "total_deduplicated": 26,
    "sources_detail": { ... },
    "duration_seconds": 1.25
  }
}
```

### 2.2 获取可用数据源列表

```
GET /api/v1/data/sources
```

**响应示例：**
```json
{
  "data": {
    "sources": [
      { "name": "boss_zhipin", "description": "BOSS直聘数据源" },
      { "name": "zhilian", "description": "智联招聘数据源" },
      { "name": "liepin", "description": "猎聘数据源" },
      { "name": "github", "description": "GitHub数据源" },
      { "name": "industry_report", "description": "行业报告数据源" }
    ]
  }
}
```

### 2.3 获取采集统计

```
GET /api/v1/data/stats
```

---

## 三、知识图谱模块

### 3.1 获取图谱统计

```
GET /api/v1/graph/stats
```

**响应示例：**
```json
{
  "data": {
    "stats": {
      "nodes": { "total": 180, "by_label": { "Skill": 120, "Job": 40, "Domain": 8, "Category": 12 } },
      "edges": { "total": 342, "by_type": { "requires": 120, "belongs_to": 80, "similar_to": 60, "prefers": 42, "evolves_to": 40 } }
    },
    "job_count": 35,
    "skill_sample": [ ... ],
    "domains": [
      { "name": "人工智能", "description": "AI相关技能领域" },
      { "name": "大数据", "description": "大数据相关技能领域" }
    ]
  }
}
```

### 3.2 获取岗位列表

```
GET /api/v1/graph/jobs?status=active
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `status` | string | 否 | 岗位状态，可选 `active` / `all`，默认 `active` |

**响应示例：**
```json
{
  "data": {
    "jobs": [
      { "title": "AI应用开发工程师", "category": "人工智能", "level": "中级", "status": "active" }
    ],
    "count": 35
  }
}
```

### 3.3 获取技能列表

```
GET /api/v1/graph/skills?domain=人工智能&limit=100
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `domain` | string | 否 | 按领域过滤 |
| `limit` | int | 否 | 返回数量上限，默认 100 |

### 3.4 获取岗位所需技能

```
GET /api/v1/graph/job/{job_title}/skills
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `job_title` | path | 岗位名称（URL编码） |

**响应示例：**
```json
{
  "data": {
    "job_title": "AI应用开发工程师",
    "required_skills": [
      { "skill_name": "Python", "confidence": 0.95, "relation_type": "requires", "level": "精通" }
    ],
    "optional_skills": [
      { "skill_name": "LangChain", "confidence": 0.75, "relation_type": "prefers", "level": "熟练" }
    ]
  }
}
```

### 3.5 初始化图谱

```
POST /api/v1/graph/initialize
```

> 首次使用或重建时调用，完成 Neo4j Schema 创建和种子数据导入。

### 3.6 从采集数据构建图谱

```
POST /api/v1/graph/build
```

> 先自动执行数据采集，再用采集结果构建/更新知识图谱。

**响应示例：**
```json
{
  "data": {
    "total_collected": 26,
    "total_deduplicated": 26,
    "skills_added": 156,
    "jobs_updated": 35
  }
}
```

---

## 四、简历解析模块

### 4.1 上传并解析简历

```
POST /api/v1/resume/upload
```

**请求格式：** `multipart/form-data`

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `file` | File | 是 | 简历文件，支持 `.pdf` / `.docx` / `.txt` |

**成功响应：**
```json
{
  "data": {
    "resume_id": "a1b2c3d4",
    "name": "张三",
    "skill_count": 12,
    "credibility_score": 0.82,
    "technical_level": "高级",
    "parsing_time_ms": 0
  }
}
```

### 4.2 获取简历画像

```
GET /api/v1/resume/{resume_id}/profile
```

**响应示例：**
```json
{
  "data": {
    "name": "张三",
    "skills_explicit": ["Python", "Java", "Docker", "Kubernetes"],
    "skills_implicit": ["分布式系统设计", "高并发架构", "微服务治理"],
    "skills_with_credibility": [
      { "skill": "Python", "credibility_level": "certified", "score": 1.0, "source": "教育经历" }
    ],
    "projects": [
      { "name": "企业级知识库平台", "role": "后端负责人", "tech_stack": ["LangChain", "RAG", "FastAPI"], "description": "..." }
    ],
    "experience_years": 5.0,
    "technical_level": "高级",
    "embedding_available": false
  }
}
```

---

## 五、智能匹配与分析模块

### 5.1 人岗匹配

```
POST /api/v1/analysis/match
```

**请求体 (JSON)：**
```json
{
  "resume_id": "a1b2c3d4",
  "top_n": 10,
  "filters": null
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `resume_id` | string | 是 | 简历 ID（上传后获取） |
| `top_n` | int | 否 | 返回前 N 个匹配结果，默认 10 |
| `filters` | object | 否 | 筛选条件，如 `{ "domain": "人工智能", "salary_range": [20, 50] }` |

**成功响应：**
```json
{
  "data": {
    "matches": [
      {
        "job_title": "AI应用开发工程师",
        "match_score": 0.87,
        "breakdown": { "skill_match": 0.82, "graph_path": 0.15, "vector_similarity": 0.72, "trend_bonus": 0.10, "credibility": 0.85 },
        "matched_skills": ["Python", "LangChain", "Docker"],
        "missing_critical": ["RAG系统设计"],
        "explanation": "张三匹配AI应用开发工程师(87%)...\n\n📊 技能匹配(82%): Python(精通)✅ LangChain(熟练)✅ Docker(熟练)✅\n📊 图路径匹配(15%): 最短路径2步\n📊 向量相似度(72%): 语义高度相关\n📊 趋势加分(+10%): 市场热度上升中\n📊 可信度(85%): 技能可信度良好"
      }
    ],
    "total_scanned": 35,
    "best_match": { ... }
  }
}
```

### 5.2 差距分析

```
POST /api/v1/analysis/gap
```

**请求体 (JSON)：**
```json
{
  "resume_id": "a1b2c3d4",
  "target_job": "AI应用开发工程师"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `resume_id` | string | 是 | 简历 ID |
| `target_job` | string | 否 | 目标岗位，不指定则做全面分析 |

**成功响应：**
```json
{
  "data": {
    "target_job": "AI应用开发工程师",
    "match_rate": 0.72,
    "matched_skills": ["Python", "LangChain", "Docker"],
    "missing_critical": ["RAG系统设计", "向量数据库"],
    "missing_optional": ["Kubernetes", "TensorFlow"],
    "learning_path": {
      "title": "AI应用开发工程师 → 学习路径",
      "steps": [
        { "step": 1, "skill": "RAG系统设计", "difficulty": "中等", "estimated_hours": 40, "resources": ["LangChain官方文档", "DeepLearning.AI课程"], "roi_score": 9.2 },
        { "step": 2, "skill": "向量数据库", "difficulty": "中等", "estimated_hours": 20, "resources": ["ChromaDB教程", "Milvus实战"], "roi_score": 8.5 }
      ]
    },
    "roi_analysis": {
      "total_investment_hours": 60,
      "expected_salary_increase": "15-25%",
      "market_demand": "高",
      "career_outlook": "AI应用开发是2026年最热门方向之一"
    },
    "summary": "张三已有Python、LangChain等基础，补足RAG和向量数据库后匹配度可提升至92%"
  }
}
```

### 5.3 What-If 假设分析

```
POST /api/v1/analysis/whatif
```

**请求体 (JSON)：**
```json
{
  "resume_id": "a1b2c3d4",
  "added_skills": ["RAG系统设计", "Kubernetes", "TensorFlow"]
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `resume_id` | string | 是 | 简历 ID |
| `added_skills` | string[] | 是 | 假设新增的技能列表 |

**成功响应：**
```json
{
  "data": {
    "original_top3": [
      { "job_title": "Java后端开发", "score": 0.78 },
      { "job_title": "全栈开发工程师", "score": 0.72 }
    ],
    "enhanced_top3": [
      { "job_title": "AI应用开发工程师", "score": 0.92 },
      { "job_title": "大模型应用工程师", "score": 0.85 }
    ],
    "comparison": {
      "best_original": { "job": "Java后端开发", "score": 0.78 },
      "best_enhanced": { "job": "AI应用开发工程师", "score": 0.92 },
      "improvement": 0.14
    },
    "recommendation": "建议优先学习RAG系统设计(ROI最高)，配合已有Python基础可在2个月内转型AI方向"
  }
}
```

---

## 六、岗位发现模块

### 6.1 触发新岗位发现

```
POST /api/v1/jobs/discover
```

> 先执行数据采集，再用 LLM 发现新岗位定义。

**响应示例：**
```json
{
  "data": {
    "candidates": [
      {
        "title": "大模型安全工程师",
        "confidence": 0.88,
        "core_skills": ["Prompt注入防护", "模型红队测试", "数据脱敏", "安全对齐"],
        "growth_rate": 0.95,
        "sources": ["行业报告", "GitHub趋势"],
        "definition": "负责大模型应用的安全评估与防护...",
        "status": "pending"
      }
    ],
    "discovered_count": 3,
    "discovery_time": "2026-06-18T19:00:00"
  }
]
```

### 6.2 审核批准/驳回岗位

```
POST /api/v1/jobs/approve
```

**请求体 (JSON)：**
```json
{
  "candidate_title": "大模型安全工程师",
  "approved": true,
  "reviewer": "admin",
  "comment": "符合市场趋势"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| `candidate_title` | string | 是 | 候选岗位名称 |
| `approved` | bool | 是 | `true` = 批准入库，`false` = 驳回 |
| `reviewer` | string | 否 | 审核人，默认 `admin` |
| `comment` | string | 否 | 审核备注 |

### 6.3 获取候选岗位列表

```
GET /api/v1/jobs/candidates
```

### 6.4 获取岗位市场情报

```
GET /api/v1/jobs/market/{job_title}
```

**响应示例：**
```json
{
  "data": {
    "job_title": "AI应用开发工程师",
    "openings": 350,
    "salary_range": [35000, 60000],
    "trend": "rising",
    "top_skills": [
      { "skill": "Python", "demand": 9.5 },
      { "skill": "LangChain", "demand": 8.8 }
    ],
    "city_distribution": {
      "北京": 30, "上海": 25, "深圳": 20, "杭州": 15, "成都": 10
    }
  }
}
```

---

## 七、统一响应格式说明

### 成功响应
```json
{
  "success": true,
  "message": "操作成功描述",
  "data": { ... },
  "timestamp": "2026-06-18T19:00:00.000000"
}
```

### 错误响应
```json
{
  "success": false,
  "error": "错误描述",
  "detail": "ExceptionType"
}
```

### HTTP 状态码

| 状态码 | 含义 |
|:------:|------|
| 200 | 请求成功 |
| 400 | 请求参数错误（文件格式不支持等） |
| 404 | 资源未找到（简历、岗位等） |
| 422 | 参数校验失败 |
| 500 | 服务器内部错误 |

---

## 八、接口清单速览

| # | 方法 | 路径 | 模块 |
|:-:|:----:|------|:----:|
| 1 | GET | `/health` | 系统 |
| 2 | GET | `/` | 系统 |
| 3 | POST | `/api/v1/data/collect` | 数据采集 |
| 4 | GET | `/api/v1/data/sources` | 数据采集 |
| 5 | GET | `/api/v1/data/stats` | 数据采集 |
| 6 | GET | `/api/v1/graph/stats` | 知识图谱 |
| 7 | GET | `/api/v1/graph/jobs` | 知识图谱 |
| 8 | GET | `/api/v1/graph/skills` | 知识图谱 |
| 9 | GET | `/api/v1/graph/job/{title}/skills` | 知识图谱 |
| 10 | POST | `/api/v1/graph/initialize` | 知识图谱 |
| 11 | POST | `/api/v1/graph/build` | 知识图谱 |
| 12 | POST | `/api/v1/resume/upload` | 简历解析 |
| 13 | GET | `/api/v1/resume/{id}/profile` | 简历解析 |
| 14 | POST | `/api/v1/analysis/match` | 智能匹配 |
| 15 | POST | `/api/v1/analysis/gap` | 差距分析 |
| 16 | POST | `/api/v1/analysis/whatif` | What-If 分析 |
| 17 | POST | `/api/v1/jobs/discover` | 岗位发现 |
| 18 | POST | `/api/v1/jobs/approve` | 岗位审核 |
| 19 | GET | `/api/v1/jobs/candidates` | 岗位发现 |
| 20 | GET | `/api/v1/jobs/market/{title}` | 市场情报 |
