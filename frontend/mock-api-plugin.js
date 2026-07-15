/**
 * Vite 插件：Mock API（无后端时前端可独立运行演示）
 * 拦截所有 /api/* 请求，返回模拟数据
 */

const PALETTE = {
  JobRole: '#3b82f6',
  Skill: '#10b981',
  Tool: '#f59e0b',
  Industry: '#a855f7',
  KnowledgeField: '#ec4899'
}

const CATEGORIES = {
  JobRole: ['AI应用工程师', '大模型算法工程师', '数据分析师', '前端开发', '后端开发', '全栈开发', 'DevOps', '产品经理'],
  Skill: ['Python', 'Java', 'JavaScript', 'SQL', '机器学习', '深度学习', '大模型', 'RAG', 'LangChain', 'Vue', 'React', 'Docker', 'Kubernetes', 'PyTorch', 'TensorFlow', '数据分析', '数据可视化', '推荐系统', '向量数据库', '自然语言处理'],
  Tool: ['PyMuPDF', 'FastAPI', 'PostgreSQL', 'MySQL', 'Neo4j', 'Elasticsearch', 'ChromaDB', 'Redis', 'Git', 'Jupyter'],
  Industry: ['人工智能', '金融科技', '电商零售', '医疗健康', '智能制造', '教育培训'],
  KnowledgeField: ['数学基础', '统计学', '计算机科学', '领域知识']
}

const TIMELINE = [
  { date: '2024-Q1', type: 'added', text: '新增 LangChain / RAG / 向量数据库' },
  { date: '2024-Q2', type: 'added', text: '新增 MCP / Agent 协议' },
  { date: '2024-Q3', type: 'modified', text: 'Python 熟练 → 精通' },
  { date: '2024-Q4', type: 'added', text: '新增 多模态 / VLM' },
  { date: '2025-Q1', type: 'weight_changed', text: '大模型应用权重 0.3 → 0.5' },
  { date: '2025-Q2', type: 'added', text: '新增 DeepSeek / Qwen' },
  { date: '2025-Q3', type: 'removed', text: '弱化 Struts2 / Hadoop 1.x' },
  { date: '2025-Q4', type: 'added', text: '新增 Agentic Workflow / Tool Use' },
  { date: '2026-Q1', type: 'modified', text: 'RAG 必备 → 熟练即可' },
  { date: '2026-Q2', type: 'weight_changed', text: 'Agent 工程化权重 0.2 → 0.45' }
]

let mockState = {
  jd_count: 128,
  resume_count: 36,
  role_count: 12,
  match_count: 28,
  jds: [],
  resumes: [],
  roles: [],
  matches: []
}

// 初始化模拟数据
function initMockData() {
  if (mockState.jds.length > 0) return
  const sources = ['BOSS直聘', '智联招聘', '猎聘', '领英', '企业官网']
  const companies = ['字节跳动', '腾讯', '阿里巴巴', '美团', '京东', '小米', '华为', '科大讯飞', '商汤科技', '旷视科技', '依图科技', '云从科技']
  for (let i = 0; i < 128; i++) {
    mockState.jds.push({
      jd_id: `JD-${String(i + 1).padStart(4, '0')}`,
      source: sources[i % sources.length],
      source_url: `https://example.com/jd/${i + 1}`,
      company: companies[i % companies.length],
      title: CATEGORIES.JobRole[i % CATEGORIES.JobRole.length],
      category: '技术',
      level: ['初级', '中级', '高级', '资深'][i % 4],
      location: ['北京', '上海', '深圳', '杭州', '广州'][i % 5],
      salary_range: `${20 + (i % 20)}K-${30 + (i % 30)}K`,
      raw_text: `负责${CATEGORIES.JobRole[i % CATEGORIES.JobRole.length]}相关工作，熟悉${CATEGORIES.Skill[i % CATEGORIES.Skill.length]}等。`,
      skills: [CATEGORIES.Skill[i % CATEGORIES.Skill.length], CATEGORIES.Skill[(i + 5) % CATEGORIES.Skill.length], CATEGORIES.Skill[(i + 10) % CATEGORIES.Skill.length]],
      published_at: '2025-12-01T00:00:00',
      crawled_at: '2025-12-15T00:00:00',
      credibility_score: 0.7 + (i % 3) * 0.1,
      is_processed: 1,
      is_duplicate: 0
    })
  }
  for (let i = 0; i < 36; i++) {
    mockState.resumes.push({
      resume_id: `R-${String(i + 1).padStart(4, '0')}`,
      file_name: `resume_${i + 1}.pdf`,
      file_type: i % 2 ? 'pdf' : 'docx',
      file_size: 102400 + i * 1024,
      file_path: `/uploads/resume_${i + 1}.${i % 2 ? 'pdf' : 'docx'}`,
      name: `候选人${i + 1}`,
      education: [{ school: '清华大学', degree: '硕士', major: '计算机科学' }],
      work_experience: [{ company: companies[i % companies.length], title: CATEGORIES.JobRole[i % CATEGORIES.JobRole.length], duration: '2年' }],
      projects: [{ name: '项目A', description: 'AI应用' }],
      skills: [CATEGORIES.Skill[i % CATEGORIES.Skill.length], CATEGORIES.Skill[(i + 3) % CATEGORIES.Skill.length], CATEGORIES.Skill[(i + 7) % CATEGORIES.Skill.length]],
      uploaded_at: '2025-12-10T00:00:00',
      parse_status: 'success',
      parse_accuracy: 0.92
    })
  }
  for (let i = 0; i < 12; i++) {
    mockState.roles.push({
      role_id: `ROLE-${String(i + 1).padStart(4, '0')}`,
      name: CATEGORIES.JobRole[i % CATEGORIES.JobRole.length],
      category: '技术',
      level: ['初级', '中级', '高级', '资深'][i % 4],
      core_responsibilities: ['设计系统架构', '主导核心模块开发', '团队技术指导'],
      required_skills: [CATEGORIES.Skill[i % CATEGORIES.Skill.length], CATEGORIES.Skill[(i + 1) % CATEGORIES.Skill.length], CATEGORIES.Skill[(i + 2) % CATEGORIES.Skill.length]],
      preferred_skills: [CATEGORIES.Skill[(i + 3) % CATEGORIES.Skill.length], CATEGORIES.Skill[(i + 4) % CATEGORIES.Skill.length]],
      typical_scenarios: ['大模型应用', '数据处理', '系统优化'],
      confidence: 0.75 + (i % 3) * 0.05,
      is_new: i < 4 ? 1 : 0,
      is_reviewed: i % 2,
      evidence_sources: [`JD-${i + 1}`, `JD-${i + 2}`],
      created_at: '2025-12-01T00:00:00',
      updated_at: '2025-12-15T00:00:00'
    })
  }
  for (let i = 0; i < 28; i++) {
    mockState.matches.push({
      id: i + 1,
      resume_id: `R-${String((i % 36) + 1).padStart(4, '0')}`,
      target_id: `ROLE-${String((i % 12) + 1).padStart(4, '0')}`,
      target_type: i % 3 === 0 ? 'jd' : 'role',
      overall_score: 0.5 + (i % 5) * 0.1,
      required_score: 0.6 + (i % 4) * 0.1,
      preferred_score: 0.4 + (i % 5) * 0.1,
      depth_score: 0.5 + (i % 6) * 0.08,
      domain_score: 0.6 + (i % 4) * 0.1,
      created_at: '2025-12-15T00:00:00'
    })
  }
}

initMockData()

// 生成图谱数据
function buildGraphData(viewType = 'default', limit = 60) {
  const nodes = []
  const edges = []
  let nodeId = 0
  const allNodeNames = []

  // 添加岗位
  CATEGORIES.JobRole.slice(0, 6).forEach((name) => {
    nodes.push({ id: `jr_${nodeId}`, label: name, type: 'JobRole', category: 'AI/技术', size: 36, color: PALETTE.JobRole })
    allNodeNames.push({ id: `jr_${nodeId}`, name, type: 'JobRole' })
    nodeId++
  })

  // 添加技能
  let skillCount = 0
  CATEGORIES.Skill.forEach((name) => {
    if (skillCount >= limit - 10) return
    nodes.push({ id: `sk_${nodeId}`, label: name, type: 'Skill', category: 'AI/编程', size: 26, color: PALETTE.Skill })
    allNodeNames.push({ id: `sk_${nodeId}`, name, type: 'Skill' })
    nodeId++
    skillCount++
  })

  // 添加工具
  CATEGORIES.Tool.slice(0, 6).forEach((name) => {
    nodes.push({ id: `tl_${nodeId}`, label: name, type: 'Tool', category: 'DevOps/工具', size: 22, color: PALETTE.Tool })
    allNodeNames.push({ id: `tl_${nodeId}`, name, type: 'Tool' })
    nodeId++
  })

  // 添加行业
  CATEGORIES.Industry.slice(0, 4).forEach((name) => {
    nodes.push({ id: `in_${nodeId}`, label: name, type: 'Industry', category: '行业', size: 30, color: PALETTE.Industry })
    allNodeNames.push({ id: `in_${nodeId}`, name, type: 'Industry' })
    nodeId++
  })

  // 边：岗位-技能 (REQUIRES)
  for (let i = 0; i < 6; i++) {
    const jobNode = allNodeNames[i]
    const skills = allNodeNames.filter(n => n.type === 'Skill')
    skills.slice(0, 5 + (i % 3)).forEach((sk) => {
      edges.push({ source: jobNode.id, target: sk.id, type: 'REQUIRES', weight: 0.6 + (i % 4) * 0.1 })
    })
  }

  // 边：技能-工具 (OFTEN_USED_WITH)
  const tools = allNodeNames.filter(n => n.type === 'Tool')
  for (let i = 0; i < tools.length; i++) {
    const skills = allNodeNames.filter(n => n.type === 'Skill')
    skills.slice(i, i + 2).forEach((sk) => {
      edges.push({ source: sk.id, target: tools[i].id, type: 'OFTEN_USED_WITH', weight: 0.5 })
    })
  }

  // 边：技能-技能 (DEPENDS_ON)
  const skList = allNodeNames.filter(n => n.type === 'Skill')
  for (let i = 0; i < skList.length - 1; i++) {
    if (i % 3 === 0 && i + 1 < skList.length) {
      edges.push({ source: skList[i].id, target: skList[i + 1].id, type: 'DEPENDS_ON', weight: 0.4 })
    }
  }

  // 边：岗位-行业 (BELONGS_TO)
  const inds = allNodeNames.filter(n => n.type === 'Industry')
  for (let i = 0; i < 6; i++) {
    edges.push({ source: allNodeNames[i].id, target: inds[i % inds.length].id, type: 'BELONGS_TO', weight: 0.7 })
  }

  return { nodes, edges }
}

function buildRoleTopN() {
  return CATEGORIES.JobRole.slice(0, 8).map((name, i) => ({
    role_id: `ROLE-${i + 1}`,
    name,
    score: 0.95 - i * 0.07,
    matched_skills: CATEGORIES.Skill.slice(i, i + 4),
    gap_skills: CATEGORIES.Skill.slice(i + 4, i + 6).map(s => ({ name: s, level: '基础', priority: i % 2 ? 'P0' : 'P1' }))
  }))
}

function buildMatchResult(targetType = 'role', targetId = 'ROLE-1') {
  return {
    overall_score: 0.82,
    required_score: 0.85,
    preferred_score: 0.72,
    depth_score: 0.78,
    domain_score: 0.88,
    breakdown: {
      required: { matched: ['Python', '机器学习'], missing: ['LangChain'] },
      preferred: { matched: ['Docker'], missing: ['RAG'] },
      depth: [{ skill: 'Python', required: '精通', current: '熟练', gap: 0.3 }],
      domain: { current: 'AI', target: 'AI', overlap: 0.9 }
    },
    gap_skills: [
      { name: 'LangChain', level: '熟练', priority: 'P0', learning_hours: 24 },
      { name: 'RAG', level: '基础', priority: 'P1', learning_hours: 16 },
      { name: '向量数据库', level: '基础', priority: 'P1', learning_hours: 12 }
    ],
    recommendations: [
      '优先学习 LangChain 框架（24小时）',
      '通过 RAG 实战项目掌握核心模式',
      '补充向量数据库（ChromaDB）实践'
    ],
    learning_path: [
      { stage: 1, name: 'Python 进阶', hours: 16, resources: ['官方文档', 'Advanced Python Tutorial'] },
      { stage: 2, name: 'LangChain 基础', hours: 24, resources: ['LangChain 官方教程', '动手做 RAG 项目'] },
      { stage: 3, name: 'RAG 实战', hours: 24, resources: ['RAG 系统设计', '向量数据库实践'] },
      { stage: 4, name: 'Agent 工程化', hours: 32, resources: ['Agent 模式', 'MCP 协议'] }
    ]
  }
}

function ok(data) {
  return { code: 0, message: 'success', data }
}

function paginate(list, page = 1, pageSize = 20) {
  const total = list.length
  const start = (page - 1) * pageSize
  return {
    items: list.slice(start, start + pageSize),
    pagination: { page, page_size: pageSize, total, total_pages: Math.ceil(total / pageSize) }
  }
}

export default function mockApiPlugin() {
  return {
    name: 'mock-api',
    configureServer(server) {
      server.middlewares.use('/api', (req, res, next) => {
        // 解析 query
        const url = req.url || ''
        const path = url.split('?')[0]
        const params = new URLSearchParams(url.split('?')[1] || '')

        // CORS
        res.setHeader('Access-Control-Allow-Origin', '*')
        res.setHeader('Content-Type', 'application/json; charset=utf-8')

        // 健康检查
        if (path === '/health' || path === '/health/' || path === '/health/basic') {
          return res.end(JSON.stringify(ok({ status: 'ok', neo4j: false, elasticsearch: false, mysql: false, mode: 'mock' })))
        }
        if (path === '/health/ready' || path === '/health/live') {
          return res.end(JSON.stringify(ok({ ready: true })))
        }
        if (path === '/' || path === '') {
          return res.end(JSON.stringify(ok({ name: 'CompetencyGraph (Mock Mode)', version: '1.0.0' })))
        }

        // JD 管理
        if (path === '/jd/list' || path === '/jd/') {
          return res.end(JSON.stringify(ok(paginate(mockState.jds, +params.get('page') || 1, +params.get('page_size') || 20))))
        }
        if (path.startsWith('/jd/')) {
          const id = path.replace('/jd/', '')
          const jd = mockState.jds.find(j => j.jd_id === id)
          if (jd) return res.end(JSON.stringify(ok(jd)))
        }

        // 简历
        if (path === '/resume/list' || path === '/resume/') {
          return res.end(JSON.stringify(ok(paginate(mockState.resumes, +params.get('page') || 1, +params.get('page_size') || 20))))
        }

        // 图谱
        if (path === '/graph/export' || path.startsWith('/graph/view/')) {
          const viewType = path === '/graph/export' ? (params.get('view_type') || 'default') : path.split('/').pop()
          return res.end(JSON.stringify(ok(buildGraphData(viewType, +params.get('limit') || 60))))
        }
        if (path === '/graph/timeline' || path.startsWith('/graph/timeline/')) {
          return res.end(JSON.stringify(ok(TIMELINE)))
        }
        if (path.startsWith('/graph/skill/') && path.includes('/dependencies')) {
          return res.end(JSON.stringify(ok(buildGraphData('default', 30))))
        }
        if (path.startsWith('/graph/skill/') && path.includes('/related_jobs')) {
          return res.end(JSON.stringify(ok(CATEGORIES.JobRole.slice(0, 5).map((name, i) => ({ name, score: 0.9 - i * 0.1 })))))
        }
        if (path.startsWith('/graph/jobrole/')) {
          return res.end(JSON.stringify(ok(mockState.roles[0])))
        }

        // 人岗匹配
        if (path === '/match/jd') {
          return res.end(JSON.stringify(ok(buildMatchResult('jd'))))
        }
        if (path === '/match/role') {
          return res.end(JSON.stringify(ok(buildMatchResult('role'))))
        }
        if (path === '/match/list' || path === '/match/') {
          return res.end(JSON.stringify(ok(paginate(mockState.matches, +params.get('page') || 1, +params.get('page_size') || 20))))
        }
        if (path === '/match/topn') {
          return res.end(JSON.stringify(ok(buildRoleTopN())))
        }

        // 岗位管理
        if (path === '/role/list' || path === '/role/') {
          return res.end(JSON.stringify(ok(paginate(mockState.roles, +params.get('page') || 1, +params.get('page_size') || 20))))
        }
        if (path === '/role/discover') {
          return res.end(JSON.stringify(ok(mockState.roles.filter(r => r.is_new))))
        }
        if (path === '/role/updates') {
          return res.end(JSON.stringify(ok(TIMELINE.map((t, i) => ({ id: i + 1, ...t, role_name: CATEGORIES.JobRole[i % 6] })))))
        }
        if (path === '/role/audit') {
          return res.end(JSON.stringify(ok(mockState.roles.filter(r => !r.is_reviewed).map(r => ({ ...r, reason: '新岗位需要人工审核' })))))
        }
        if (path.startsWith('/role/') && (path.endsWith('/approve') || path.endsWith('/reject') || path.endsWith('/modify'))) {
          return res.end(JSON.stringify(ok({ success: true })))
        }
        if (path === '/role/discover/trigger') {
          return res.end(JSON.stringify(ok({ discovered: 3 })))
        }

        // 数据采集
        if (path === '/crawl/start') {
          return res.end(JSON.stringify(ok({ task_id: 'T-' + Date.now(), status: 'running' })))
        }
        if (path === '/crawl/status') {
          return res.end(JSON.stringify(ok({ status: 'success', total: 128, success: 120, failed: 8 })))
        }
        if (path === '/crawl/mock') {
          return res.end(JSON.stringify(ok({ jd_created: 50, resume_created: 20, role_created: 10 })))
        }

        // 兜底
        next()
      })
    }
  }
}
