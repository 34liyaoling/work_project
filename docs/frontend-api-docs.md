# 前端开发指南 — 知识图谱系统

## 一、架构概述

### 1.1 前端技术栈

| 技术 | 用途 |
|------|------|
| Vue 3 (Composition API + `<script setup>`) | 框架 |
| Vue Router | 路由 |
| Pinia | 全局状态管理 |
| Element Plus | UI 组件库 |
| ECharts | 图表 |
| Axios | HTTP 请求 |

### 1.2 数据流

```
用户操作 → 页面组件 → api/index.js (axios) → 后端 API → Neo4j/ChromaDB/LLM
                                                      ↓
后端返回 ApiResponse { success, message, data, timestamp }
                                                      ↓
axios 拦截器剥一层 → 组件拿到 { success, message, data, timestamp }
```

**关键**：axios 拦截器做了 `response => response.data`，所以组件中拿到的 `res` 就是后端的完整 JSON（含 `success`、`message`、`data`、`timestamp`）。**不是直接拿 data 层**。

### 1.3 页面路由清单

| 路由 path | name | 页面 | 需要简历上下文 |
|-----------|------|------|--------------|
| `/dashboard` | `Dashboard` | 数据驾驶舱 | 否 |
| `/graph-explorer` | `GraphExplorer` | 图谱浏览器 | 否 |
| `/resume-analysis` | `ResumeAnalysis` | 简历分析 | **写入方** |
| `/job-matching` | `JobMatching` | 智能匹配 | ✅ 是 |
| `/job-discovery` | `JobDiscovery` | 新岗位发现 | 否 |
| `/gap-analysis` | `GapAnalysis` | 差距分析 | ✅ 是 |
| `/career-path` | `CareerPath` | 职业路径 | 否 |
| `/market-intelligence` | `MarketIntelligence` | 市场情报 | 否 |
| `/what-if-analysis` | `WhatIfAnalysis` | What-If分析 | ✅ 是 |
| `/batch-analysis` | `BatchAnalysis` | 批量分析 | 否 |
| `/qa-assistant` | `QaAssistant` | 智能问答 | 否 |
| `/admin-panel` | `AdminPanel` | 系统管理 | 否 |

---

## 二、核心要求：简历上下文持久化

### 2.1 问题

用户上传简历后，`resume_id` 存在 Pinia store 的内存中。一旦刷新页面或关闭浏览器，store 清空，其他功能（匹配/差距/WhatIf）就找不到简历了。

### 2.2 解决方案

给 Pinia store 加 localStorage 持久化。流程图：

```
简历分析页上传成功
       ↓
setResume(id, name, skills, score)
       ↓
写入 Pinia store (内存)
       ↓
写入 localStorage (磁盘)
```

```
刷新页面后
       ↓
Pinia store 初始化时从 localStorage 读取
       ↓
内存恢复 resumeId/candidateName/skills
       ↓
其他页面 onMounted 检测到 resumeId → 自动代入
```

### 2.3 具体实现

修改 `src/stores/resume.js`，加 localStorage 读写：

```javascript
import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_KEY = 'kg_resume_context'

export const useResumeStore = defineStore('resume', () => {
  // 从 localStorage 恢复
  const saved = (() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      return raw ? JSON.parse(raw) : {}
    } catch {
      return {}
    }
  })()

  const resumeId = ref(saved.resumeId || '')
  const candidateName = ref(saved.candidateName || '')
  const skills = ref(saved.skills || [])
  const credibilityScore = ref(saved.credibilityScore ?? null)

  function _persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        resumeId: resumeId.value,
        candidateName: candidateName.value,
        skills: skills.value,
        credibilityScore: credibilityScore.value
      }))
    } catch { /* localStorage 不可用时静默失败 */ }
  }

  function setResume(id, name, skillList, score = null) {
    resumeId.value = id
    candidateName.value = name || ''
    skills.value = skillList || []
    credibilityScore.value = score
    _persist()
  }

  function clear() {
    resumeId.value = ''
    candidateName.value = ''
    skills.value = []
    credibilityScore.value = null
    try { localStorage.removeItem(STORAGE_KEY) } catch {}
  }

  return { resumeId, candidateName, skills, credibilityScore, setResume, clear }
})
```

---

## 三、API 接口完整文档

> **注意**：以下响应格式为**经过 axios 拦截器后的格式**，即后端原始 JSON 的完整内容（含 `success`、`message`、`data`、`timestamp`）。

### 3.1 统一响应模型

```typescript
// 所有 API 统一使用此结构
interface ApiResponse<T = any> {
  success: boolean       // true 成功 / false 失败
  message: string       // 提示信息
  data: T | null        // 业务数据
  timestamp: string     // ISO 时间戳，如 "2026-07-10T09:30:00.123456"
}
```

---

### 3.2 简历分析 — `/api/resume/*`

#### POST `/api/resume/upload` — 上传并解析简历文件

```
Content-Type: multipart/form-data
Body: file (UploadFile) — 支持 pdf / docx / txt
```

响应示例（成功）：
```json
{
  "success": true,
  "message": "简历解析完成",
  "data": {
    "resume_id": "8c41548d7d99c0a2",
    "name": "李康",
    "skill_count": 20,
    "credibility_score": 0.59,
    "technical_level": "mid",
    "parsing_time_ms": 0
  },
  "timestamp": "2026-07-10T09:30:00.123456"
}
```

#### POST `/api/resume/upload-text` — 直接提交简历文本

```
Content-Type: application/x-www-form-urlencoded
Body: content (string) — 简历纯文本内容
```

响应格式同上。

#### GET `/api/resume/{resume_id}/profile` — 获取简历画像

```
Path: resume_id (string) — 上传返回的 resume_id
```

响应示例：
```json
{
  "success": true,
  "message": "ok",
  "data": {
    "name": "李康",
    "phone": "152-9021-3570",
    "email": "3052936294@qq.com",
    "intent": null,
    "skills_explicit": ["Python", "Java", "Flask", "YOLO", "TypeScript", "C++"],
    "skills_implicit": ["LangChain", "RAG系统设计", "OAuth2/JWT", "SQL注入防护"],
    "skills_with_credibility": [],
    "projects": [
      {
        "project_name": "智能摔倒检测系统",
        "role": "后端和模型训练",
        "technologies_used": ["Python", "Flask", "YOLO"],
        "description": "用Flask写后端接口...",
        "highlights": [],
        "time_range": "2025.09 -2025.11",
        "complexity_score": 0.65
      }
    ],
    "work_experience": [],
    "education": [],
    "experience_years": 0,
    "technical_level": "mid",
    "credibility_score": null,
    "embedding_available": false
  },
  "timestamp": "2026-07-10T09:30:00.123456"
}
```

**前端字段映射**（从后端字段 → 模板显示字段）：
```
后端字段                  前端模板字段
──────────────────────────────────────
name                  →  resumeData.name
email                 →  resumeData.email
phone                 →  resumeData.phone
skills_explicit + skills_implicit → resumeData.skills (合并)
credibility_score     →  resumeData.credibilityScore
projects[].project_name → resumeData.projects[].name
projects[].technologies_used → resumeData.projects[].techStack
```

---

### 3.3 人岗匹配 — `/api/matching/*`

#### POST `/api/matching/match` — 执行匹配

```json
// Request
{
  "resume_id": "8c41548d7d99c0a2",    // 必填
  "top_n": 10,                         // 可选，默认10
  "filters": {                         // 可选
    "domain": "人工智能",
    "salary_range": [10000, 30000],
    "location": "北京"
  }
}
```

响应：
```json
{
  "success": true,
  "message": "ok",
  "data": {
    "matches": [
      {
        "job_title": "Python开发工程师",
        "match_score": 0.85,
        "breakdown": {},
        "matched_skills": ["Python", "Flask"],
        "missing_critical": ["Docker"],
        "explanation": "候选人在Python和Flask方面有项目经验..."
      }
    ],
    "total_scanned": 538,
    "best_match": { "... same structure as match item ..." }
  }
}
```

#### POST `/api/matching/gap` — 差距分析

```json
// Request
{
  "resume_id": "8c41548d7d99c0a2",     // 必填
  "target_job": "Python开发工程师"       // 必填
}
```

响应：
```json
{
  "success": true,
  "message": "ok",
  "data": {
    "target_job": "Python开发工程师",
    "match_rate": 0.65,
    "matched_skills": ["Python", "Flask"],
    "missing_critical": ["Docker", "MySQL"],
    "missing_optional": ["Kubernetes"],
    "learning_path": {
      "steps": [
        { "skillName": "Docker", "difficulty": "中等", "duration": "2周", "resources": ["Docker官方文档"], "roiScore": 85 }
      ]
    },
    "roi_analysis": { "...": "..." },
    "summary": "候选人需要在容器化和数据库方面补充..."
  }
}
```

#### POST `/api/matching/whatif` — What-If 假设分析

```json
// Request
{
  "resume_id": "8c41548d7d99c0a2",     // 必填
  "added_skills": ["Docker", "Kubernetes"]   // 必填，要新增的技能列表
}
```

响应：
```json
{
  "success": true,
  "message": "ok",
  "data": {
    "original_top3": [{"job_title": "...", "match_score": 0.85}],
    "enhanced_top3": [{"job_title": "...", "match_score": 0.92}],
    "comparison": { "score_improvements": {...}, "new_opportunities": [...] },
    "recommendation": "推荐优先学习Docker，可提升12个岗位的匹配率"
  }
}
```

---

### 3.4 知识图谱 — `/api/graph/*`

#### GET `/api/graph/stats` — 图谱统计

```
Query: 无
```

```json
{
  "success": true,
  "data": {
    "stats": { "nodes": 766, "edges": 1263 },
    "job_count": 538,
    "skill_sample": ["Python", "Java", "Flask"],
    "domains": ["人工智能", "前端开发", "后端开发"]
  }
}
```

#### GET `/api/graph/jobs` — 获取所有岗位

```
Query: status (string) — 默认 "all"
```

```json
{
  "success": true,
  "data": {
    "jobs": [
      { "id": "job_001", "title": "Python开发工程师", "domain": "后端开发", "category": "技术" }
    ],
    "count": 538
  }
}
```

#### GET `/api/graph/skills` — 获取技能列表

```
Query: domain (string, optional, 按领域过滤)
       limit (number, 默认100)
```

```json
{
  "success": true,
  "data": {
    "skills": ["Python", "Java", "Flask", "Docker"],
    "count": 100
  }
}
```

#### GET `/api/graph/job/{job_title}/skills` — 岗位技能

```
Path: job_title (string)
```

```json
{
  "success": true,
  "data": {
    "job_title": "Python开发工程师",
    "required_skills": ["Python", "Flask", "MySQL"],
    "optional_skills": ["Docker", "Redis"]
  }
}
```

#### GET `/api/graph/search` — 搜索图谱

```
Query: q (string) — 搜索关键词
```

```json
{
  "success": true,
  "data": {
    "query": "Python",
    "results": [{"name": "Python", "type": "skill", "label": "编程语言"}],
    "count": 5
  }
}
```

#### POST `/api/graph/initialize` — 初始化图谱

```
Body: 无
```

#### POST `/api/graph/build` — 构建图谱

```
Body: 无
```

---

### 3.5 职业路径 — `/api/career/*`

#### POST `/api/career/plan` — 职业路径规划

```
Query: current_role (string, 默认 "")
       target_role (string, 默认 "")
       years (number, 默认5)
```

```json
{
  "success": true,
  "data": {
    "paths": [
      {
        "name": "技术深耕路线",
        "description": "...",
        "type": "technical",
        "milestones": [
          { "year": 1, "role": "初级工程师", "skills": ["Python"], "salary_range": [10000, 15000] }
        ],
        "key_technologies": ["Python", "Docker"],
        "suitable_for": ["技术专注型"]
      }
    ],
    "available_jobs": ["Python开发工程师", "Java开发工程师"],
    "total_jobs": 20
  }
}
```

#### GET `/api/career/roles` — 获取所有角色

```
Query: 无
```

```json
{
  "success": true,
  "data": {
    "roles": [
      { "title": "Python开发工程师", "domain": "后端开发", "salary_min": 10000, "salary_max": 30000 }
    ]
  }
}
```

---

### 3.6 新岗位发现 — `/api/jobs/*`

#### POST `/api/jobs/discover` — 触发发现

```
Body: 无
```

#### POST `/api/jobs/approve` — 审核岗位

```json
// Request
{
  "candidate_title": "大模型应用工程师",
  "approved": true,
  "reviewer": "admin",
  "comment": "这是一个有前景的方向"
}
```

#### GET `/api/jobs/candidates` — 获取候选岗位

```
Query: 无
```

```json
{
  "success": true,
  "data": {
    "candidates": [{"title": "大模型应用工程师", "domain": "人工智能", "confidence": 0.85}],
    "count": 3
  }
}
```

#### GET `/api/jobs/market/{job_title}` — 市场情报

```
Path: job_title (string)
```

```json
{
  "success": true,
  "data": {
    "job_title": "Python开发工程师",
    "openings": 3200,
    "salary_range": [10000, 35000],
    "trend": "↑上涨",
    "top_skills": [{"skill": "Python", "count": 2800}],
    "city_distribution": {"北京": 800, "上海": 600}
  }
}
```

---

### 3.7 批量分析 — `/api/batch/*`

#### POST `/api/batch/upload` — 批量上传

```
Content-Type: multipart/form-data
Body: files (list[UploadFile])
```

```json
{
  "success": true,
  "data": {
    "batch_id": "batch_001",
    "results": [{"resume_id": "...", "name": "..."}],
    "total": 5,
    "success": 4,
    "failed": 1
  }
}
```

#### GET `/api/batch/{batch_id}/result` — 批量结果

```
Path: batch_id (string)
```

#### GET `/api/batch/{batch_id}/gap-analysis` — 批量差距分析

```
Path: batch_id (string)
Query: target_job (string, 默认 "")
```

---

### 3.8 智能问答 — `/api/qa/*`

#### POST `/api/qa/ask` — 问答

```
Query: question (string) — 问题正文
```

```json
{
  "success": true,
  "message": "ok",
  "data": {
    "answer": "根据知识图谱数据，Python开发岗位的必备技能为：Python...",
    "sources": ["knowledge_graph", "llm"]
  },
  "timestamp": "2026-07-10T09:30:00.123456"
}
```

⚠ **空问题会返回错误**：
```json
{
  "success": false,
  "message": "问题不能为空，请输入具体问题",
  "data": null
}
```

---

### 3.9 系统管理 — `/api/system/*`

#### GET `/api/system/health` — 健康检查

#### GET `/api/system/audit-queue` — 审核队列

#### POST `/api/system/audit/{item_id}` — 审核操作

```
Query: action (string, 默认 "approve")
       note (string, 默认 "")
```

---

### 3.10 数据采集 — `/api/data/*`

#### POST `/api/data/collect` — 触发采集

```json
// Request
{
  "sources": ["lagou", "51job"],
  "limit_per_source": 50,
  "force_refresh": false
}
```

#### GET `/api/data/collect/status` — 采集状态

#### GET `/api/data/sources` — 数据源列表

#### GET `/api/data/stats` — 数据统计

#### POST `/api/data/import` — 导入数据

```json
// Request
{
  "jobs": [
    {
      "job_title": "Python开发工程师",
      "company_name": "某科技公司",
      "salary_min": 10000,
      "salary_max": 30000,
      "location": "北京",
      "skills": ["Python", "Flask"],
      "job_description": "...",
      "source": "manual",
      "source_url": ""
    }
  ],
  "skip_llm_enhance": false
}
```

#### POST `/api/data/import/file` — 文件导入

```
Content-Type: multipart/form-data
Body: file (UploadFile) — JSON 文件
```

#### GET `/api/data/import/template` — 获取导入模板

---

## 四、页面串联规范

### 4.1 需要接入 resume store 的页面

**必须接入的 4 个页面**（已有部分实现，需加的修改量小）：

| 页面 | 必须做的 |
|------|---------|
| ResumeAnalysis | ✅ 上传成功后调用 `store.setResume(id, name, skills, score)` |
| JobMatching | ✅ onMounted 时读 `store.resumeId` 自动填入 |
| GapAnalysis | ✅ onMounted 时读 `store.resumeId` 自动代入 |
| WhatIfAnalysis | ✅ onMounted 时读 `store.skills` 加载当前技能 |

**可选接入的页面**（与简历关联度低，不接也行）：

| 页面 | 要不要接 | 理由 |
|------|---------|------|
| CareerPath | 建议接 | 可用 `store.skills` 作为当前技能基线做路径规划 |
| BatchAnalysis | 不接 | 批量场景不依赖单份简历 |
| Dashboard | 不接 | 汇总面板 |
| MarketIntelligence | 不接 | 市场数据与个人简历无关 |
| JobDiscovery | 不接 | 系统级功能 |
| QA Assistant | 不接 | 通用问答不依赖简历 |
| GraphExplorer | 不接 | 图谱浏览 |
| AdminPanel | 不接 | 系统管理 |

### 4.2 页面跳转传参

页面间跳转统一用 route name + query params，不要用 sessionStorage 或其他方式：

```javascript
// 简历分析 → 岗位匹配
router.push({ name: 'JobMatching' })

// 岗位匹配 → 差距分析（带 target_job）
router.push({ name: 'GapAnalysis', query: { target_job: row.jobTitle } })
```

### 4.3 错误处理规范

所有 API 调用都需要 try-catch，且有用户可见的反馈：

```javascript
try {
  const res = await api.someMethod(params)
  const data = res?.data || res  // axios 已剥一层，data 在后端响应对象里
  // data 就是业务数据
} catch (e) {
  ElMessage.error('操作失败：' + (e.message || ''))
}
```

---

## 五、已知问题和注意事项

### 5.1 简历字段映射

后端返回的字段名用 `snake_case`（Python 风格），前端模板期望 `camelCase`。在 ResumeAnalysis 中需要做字段名映射：

```javascript
resumeData.value = {
  name: profile.name,
  credibilityScore: profile.credibility_score,
  projects: (profile.projects || []).map(p => ({
    name: p.project_name,
    role: p.role,
    techStack: p.technologies_used,
    description: p.description
  }))
}
```

### 5.2 OCR 处理时间

图片型 PDF（扫描件/截图导出）上传后需要 10-15 秒的 OCR 识别时间，页面应显示加载状态：
```html
<div v-if="uploading" class="loading-overlay">
  <el-icon :size="32"><Loading /></el-icon>
  <p>正在解析简历，请稍候...</p>
</div>
```

### 5.3 浏览器缓存

每次构建后需要 `Ctrl+F5` 强制刷新，或 F12 → Network 勾选 Disable cache。JS/CSS 文件名带 hash，但 index.html 可能被缓存。

### 5.4 智能问答 API 调用方式

QA 接口的 question 是 `Query` 参数，不是 body：

```javascript
// ✅ 正确
askQA(question) { return api.post('/qa/ask', null, { params: { question } }) }

// ❌ 错误
askQA(question) { return api.post('/qa/ask', { question }) }
```

### 5.5 404 的响应格式

当 resume_id 不存在时，后端返回 HTTP 404 + `ApiResponse` JSON：

```json
// HTTP 404
{
  "success": false,
  "message": "简历未找到，请先上传",
  "data": null,
  "timestamp": "2026-07-10T09:30:00.123456"
}
```

axios 拦截器会把非 2xx 状态码抛到 catch，所以业务代码会走到 `catch (e)` 分支。
