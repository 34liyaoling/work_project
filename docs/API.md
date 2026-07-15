# API 文档

> XH-202621 赛题 · CompetencyGraph API 参考
>
> Base URL：`http://localhost:8000/api`
> 完整 OpenAPI Schema：<http://localhost:8000/openapi.json>
> Swagger UI：<http://localhost:8000/docs>
> ReDoc：<http://localhost:8000/redoc>

## 通用约定

### 响应格式

所有 API 统一返回 `CommonResponse`：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

- `code = 0` 表示成功
- 失败时 `code` 为非 0，`message` 为错误描述

### 分页

列表类接口使用统一分页结构：

```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100
  }
}
```

### 错误码

| HTTP | 含义           |
|------|----------------|
| 400  | 请求参数错误   |
| 404  | 资源不存在     |
| 500  | 服务器内部错误 |

---

## 一、JD 管理 `/api/jd`

### POST `/api/jd/` 创建 JD

**请求体**

```json
{
  "source": "拉勾",
  "source_url": "https://...",
  "company": "字节跳动",
  "title": "算法工程师",
  "category": "算法",
  "level": "高级",
  "location": "北京",
  "salary_range": "30-50K",
  "raw_text": "岗位职责：负责...",
  "published_at": "2026-01-01T00:00:00"
}
```

**响应**

```json
{
  "code": 0,
  "data": { "jd_id": "jd_xxx" }
}
```

### GET `/api/jd/` JD 列表

**Query 参数**

| 参数         | 类型    | 说明                       |
|--------------|---------|----------------------------|
| page         | int     | 页码，默认 1               |
| page_size    | int     | 每页条数，默认 20          |
| source       | string  | 数据来源过滤               |
| company      | string  | 公司名（模糊匹配）         |
| category     | string  | 类别过滤                   |
| is_processed | int     | 0/1 处理状态               |
| keyword      | string  | 标题模糊匹配               |

### GET `/api/jd/{jd_id}` JD 详情

返回 JD 完整信息（来源、文本、解析结果、技能列表等）。

### POST `/api/jd/{jd_id}/parse` 触发解析

调用规则化解析器抽取技能，结果写入 `parsed_data` 与 `skills`。

### POST `/api/jd/batch_parse` 批量解析

```json
{
  "jd_ids": ["jd_xxx", "jd_yyy"],
  "force": false
}
```

### DELETE `/api/jd/{jd_id}` 删除 JD

---

## 二、简历解析 `/api/resume`

### POST `/api/resume/upload` 上传简历

**Content-Type**：`multipart/form-data`
**字段**：`file`（支持 .pdf / .docx / .doc）

**响应**

```json
{
  "code": 0,
  "data": {
    "resume_id": "resume_xxx",
    "file_name": "张三.pdf",
    "file_size": 102400,
    "parse_status": "pending"
  }
}
```

### GET `/api/resume/{resume_id}` 简历详情

### GET `/api/resume/` 简历列表

支持 `parse_status` / `name` 过滤。

### POST `/api/resume/{resume_id}/parse` 触发解析

```json
{ "force": false }
```

### GET `/api/resume/{resume_id}/skills` 简历技能列表

---

## 三、图谱查询 `/api/graph`

### GET `/api/graph/export` 导出图谱

供前端 G6 渲染使用。

**Query**：`view_type` = `default` / `technology_stack` / `level` / `domain`

**响应**

```json
{
  "code": 0,
  "data": {
    "nodes": [{ "id": "Python", "label": "Python", "type": "skill", "popularity": 0.9 }],
    "edges": [{ "source": "算法工程师", "target": "Python", "relation": "requires", "weight": 1.0 }],
    "metadata": { "view_type": "default" }
  }
}
```

### GET `/api/graph/view/{view_type}` 多视图查询

`view_type` ∈ {`technology_stack`, `level`, `domain`}

### GET `/api/graph/skill/{name}/dependencies` 技能依赖链

**Query**：`depth`（1-5，默认 3）

### GET `/api/graph/skill/{name}/related_jobs` 技能相关岗位

**Query**：`top_n`（1-50）

### GET `/api/graph/timeline/{skill_name}` 技能时间线

返回该技能的历史演化记录（added/removed/weight_changed/usage_changed）。

### GET `/api/graph/jobrole/{name}` 岗位详情

### POST `/api/graph/snapshot` 创建快照

```json
{ "description": "版本说明" }
```

### POST `/api/graph/snapshot/{snapshot_id}/restore` 恢复快照

---

## 四、人岗匹配 `/api/match`

### POST `/api/match/jd` 与具体 JD 匹配

**请求体**

```json
{
  "resume_id": "resume_xxx",
  "jd_id": "jd_xxx",
  "weights": {
    "required": 0.4,
    "preferred": 0.2,
    "depth": 0.25,
    "domain": 0.15
  }
}
```

**响应**

```json
{
  "code": 0,
  "data": {
    "match_id": 123,
    "overall_score": 0.85,
    "required_score": 0.9,
    "preferred_score": 0.7,
    "depth_score": 0.8,
    "domain_score": 0.85,
    "breakdown": [
      {
        "dimension": "必备技能",
        "score": 0.9,
        "weight": 0.4,
        "matched_skills": ["Python", "SQL"],
        "missing_skills": ["Spark"]
      }
    ],
    "gap_skills": [
      {
        "skill_name": "Spark",
        "status": "missing",
        "importance": 0.8,
        "suggestion": "建议通过在线课程或项目实践学习 Spark"
      }
    ],
    "recommendations": ["补齐技能：Spark", "..."],
    "learning_path": []
  }
}
```

### POST `/api/match/role` 与岗位方向匹配（Top-N）

```json
{
  "resume_id": "resume_xxx",
  "top_n": 10
}
```

**响应**

```json
{
  "code": 0,
  "data": {
    "resume_id": "resume_xxx",
    "top_n": 10,
    "results": [
      {
        "role": "算法工程师",
        "category": "算法",
        "level": "高级",
        "overall_score": 0.87,
        "required_score": 0.85,
        "matched_skills": ["Python", "机器学习"],
        "gap_skills": [...]
      }
    ]
  }
}
```

### GET `/api/match/{match_id}` 获取单次匹配

### GET `/api/match/` 匹配历史列表

支持 `resume_id` / `target_type` 过滤。

---

## 五、数据采集 `/api/crawl`

### POST `/api/crawl/start` 启动采集任务

```json
{
  "source": "拉勾",
  "keywords": ["算法", "Python"],
  "max_count": 100,
  "task_type": "incremental",
  "location": "北京"
}
```

**响应**：返回 `task_id`，可轮询 `/status/{task_id}`。

### GET `/api/crawl/status/{task_id}` 查询任务状态

### GET `/api/crawl/logs` 采集日志列表

### POST `/api/crawl/mock` 生成模拟数据

```json
{
  "jd_count": 50,
  "resume_count": 20,
  "role_count": 10
}
```

---

## 六、岗位管理 `/api/role`

### GET `/api/role/new` 新岗位发现列表

支持 `category` / `min_confidence` 过滤。

### GET `/api/role/updates` 既有岗位更新列表

**Query**：`days`（回溯天数，默认 7）

### GET `/api/role/{role_id}` 岗位详情

### GET `/api/role/` 岗位列表

### POST `/api/role/{role_id}/review` 审核岗位

```json
{
  "action": "approve",   // approve / reject / modify
  "reviewer": "admin",
  "comment": "审核意见",
  "modified_data": {     // 仅 modify 时使用
    "name": "新名称"
  }
}
```

### GET `/api/role/audit/queue` 审核队列

支持 `status` 过滤（pending/approved/rejected）。

### POST `/api/role/discover` 触发岗位发现

```json
{
  "days": 30,
  "min_source_count": 3
}
```

---

## 七、健康检查 `/api`

### GET `/api/health` 基础健康检查

```json
{
  "status": "ok",
  "service": "CompetencyGraph",
  "env": "development",
  "mysql": true,
  "neo4j": true,
  "elasticsearch": true,
  "timestamp": "2026-07-15T10:00:00"
}
```

### GET `/api/health/ready` 就绪探针（K8s）

### GET `/api/health/live` 存活探针（K8s）

---

## 八、调用示例

### cURL

```bash
# 上传简历
curl -X POST http://localhost:8000/api/resume/upload \
  -F "file=@/path/to/resume.pdf"

# 触发匹配
curl -X POST http://localhost:8000/api/match/jd \
  -H "Content-Type: application/json" \
  -d '{"resume_id":"resume_xxx","jd_id":"jd_xxx"}'

# 触发岗位发现
curl -X POST http://localhost:8000/api/role/discover \
  -H "Content-Type: application/json" \
  -d '{"days":30,"min_source_count":3}'
```

### JavaScript (axios)

```javascript
import axios from 'axios'

const api = axios.create({ baseURL: 'http://localhost:8000/api' })

// 上传简历
const form = new FormData()
form.append('file', file)
const { data } = await api.post('/resume/upload', form)

// 人岗匹配
const matchRes = await api.post('/match/jd', {
  resume_id: 'resume_xxx',
  jd_id: 'jd_xxx'
})
```

### Python

```python
import requests

r = requests.post("http://localhost:8000/api/match/jd", json={
    "resume_id": "resume_xxx",
    "jd_id": "jd_xxx"
})
result = r.json()["data"]
print(f"匹配率: {result['overall_score']:.2%}")
```

---

## 九、错误处理

所有错误响应统一格式：

```json
{
  "detail": "错误描述",
  "code": "ERROR_CODE"
}
```

或在 `CommonResponse` 中：

```json
{
  "code": 1001,
  "message": "简历不存在",
  "data": null
}
```
