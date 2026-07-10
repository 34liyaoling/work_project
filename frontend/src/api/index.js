import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.response.use(
  response => response.data,
  error => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    console.error('[API Error]', message)
    return Promise.reject(new Error(message))
  }
)

export default {
  // ==================== 简历分析 ====================
  uploadResume(file) {
    const form = new FormData()
    form.append('file', file)
    return api.post('/resume/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  uploadResumeText(content) {
    const params = new URLSearchParams()
    params.append('content', content)
    return api.post('/resume/upload-text', params, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
  },
  getResumeProfile(id) { return api.get(`/resume/${id}/profile`) },

  // ==================== 人岗匹配 ====================
  match(params) { return api.post('/matching/match', params) },
  gapAnalysis(params) { return api.post('/matching/gap', params) },
  whatIf(params) { return api.post('/matching/whatif', params) },

  // ==================== 知识图谱 ====================
  getGraphStats() { return api.get('/graph/stats') },
  getJobs(status = 'all') { return api.get('/graph/jobs', { params: { status } }) },
  getSkills(domain, limit = 100) { return api.get('/graph/skills', { params: { domain, limit } }) },
  getJobSkills(title) { return api.get(`/graph/job/${encodeURIComponent(title)}/skills`) },
  searchGraph(q) { return api.get('/graph/search', { params: { q } }) },
  initializeGraph() { return api.post('/graph/initialize') },
  buildGraph() { return api.post('/graph/build') },

  // ==================== 职业路径 ====================
  planCareer(currentRole, targetRole, years = 5) {
    return api.post('/career/plan', null, { params: { current_role: currentRole, target_role: targetRole, years } })
  },
  getCareerRoles() { return api.get('/career/roles') },

  // ==================== 新岗位发现 ====================
  discoverJobs() { return api.post('/jobs/discover') },
  approveJob(data) { return api.post('/jobs/approve', data) },
  getJobCandidates() { return api.get('/jobs/candidates') },
  getMarketIntel(title) { return api.get(`/jobs/market/${encodeURIComponent(title)}`) },

  // ==================== 智能问答 ====================
  askQA(question) { return api.post('/qa/ask', null, { params: { question } }) },

  // ==================== 批量分析 ====================
  batchUpload(files) {
    const form = new FormData()
    files.forEach(f => form.append('files', f))
    return api.post('/batch/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  getBatchResult(batchId) { return api.get(`/batch/${batchId}/result`) },
  batchGapAnalysis(batchId, targetJob = '') {
    return api.get(`/batch/${batchId}/gap-analysis`, { params: { target_job: targetJob } })
  },

  // ==================== 系统管理 ====================
  healthCheck() { return api.get('/system/health') },
  getAuditQueue() { return api.get('/system/audit-queue') },
  auditItem(itemId, action = 'approve', note = '') {
    return api.post(`/system/audit/${itemId}`, null, { params: { action, note } })
  },

  // ==================== 数据采集 ====================
  collect(params) { return api.post('/data/collect', params) },
  getCollectStatus() { return api.get('/data/collect/status') },
  getSources() { return api.get('/data/sources') },
  getDataStats() { return api.get('/data/stats') },
  importData(data, skipLlmEnhance = false) {
    return api.post('/data/import', { ...data, skip_llm_enhance: skipLlmEnhance })
  },
  importDataFile(file) {
    const form = new FormData()
    form.append('file', file)
    return api.post('/data/import/file', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  getImportTemplate() { return api.get('/data/import/template') },

  // ==================== 编排中心 ====================
  orchestrate(request, context = {}) { return api.post('/orchestrate', { request, context }) },
  analyzeIntent(request) { return api.get('/orchestrate/intent', { params: { request } }) },
  getOrchestrateAgents() { return api.get('/orchestrate/agents') },
  getOrchestrateHistory(limit = 20) { return api.get('/orchestrate/history', { params: { limit } }) },
  qualityCheck() { return api.post('/orchestrate/quality/check') },
  qualityVerify(output) { return api.post('/orchestrate/quality/verify', { output }) },
  getAuditLog(limit = 10) { return api.get('/orchestrate/quality/audit-log', { params: { limit } }) },
  getMemoryStats() { return api.get('/orchestrate/memory/stats') },
  getAgentMemory(agentName, taskType, limit = 50) {
    return api.get(`/orchestrate/memory/${agentName}`, { params: { task_type: taskType, limit } })
  },
  getEntityHistory(agentName, entityId) {
    return api.get(`/orchestrate/memory/${agentName}/entity/${entityId}`)
  },
}
