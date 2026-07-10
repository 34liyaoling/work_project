<template>
  <div class="page-container">
    <div class="page-header">
      <h2>图谱浏览器</h2>
      <p>可视化浏览知识图谱中的技能、岗位与领域关联网络</p>
    </div>

    <el-row :gutter="16">
      <el-col :span="18">
        <el-card shadow="never" class="graph-card">
          <div class="graph-toolbar">
            <div class="toolbar-left">
              <el-select v-model="nodeType" placeholder="节点类型" size="small" style="width: 120px" @change="refreshGraph">
                <el-option label="全部类型" value="all" />
                <el-option label="技能" value="skill" />
                <el-option label="岗位" value="job" />
                <el-option label="领域" value="domain" />
              </el-select>
              <el-select v-model="relType" placeholder="关系类型" size="small" style="width: 130px" @change="refreshGraph">
                <el-option label="全部关系" value="all" />
                <el-option label="需要技能" value="requires" />
                <el-option label="归属领域" value="belongs_to" />
                <el-option label="相关联" value="related" />
              </el-select>
              <el-input
                v-model="searchText"
                placeholder="搜索节点名称..."
                size="small"
                style="width: 200px"
                clearable
                @input="onSearch"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
            </div>
            <div class="toolbar-right">
              <el-button size="small" @click="zoomIn">放大</el-button>
              <el-button size="small" @click="zoomOut">缩小</el-button>
              <el-button size="small" @click="fitView">适应屏幕</el-button>
              <el-button size="small" type="primary" :loading="loading" @click="loadData">刷新数据</el-button>
            </div>
          </div>
          <div id="graph-container" class="graph-container" v-loading="loading">
            <div v-if="!hasData" class="empty-hint">
              <el-icon size="48" color="var(--el-color-info)"><Connection /></el-icon>
              <p>暂无图谱数据</p>
              <p class="empty-sub">请先执行「数据采集」操作来填充知识图谱</p>
              <el-button type="primary" @click="initDefault">初始化图谱</el-button>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stats-card">
          <template #header><span>图谱概况</span></template>
          <div class="stat-item"><span class="stat-label">节点总数</span><span class="stat-value">{{ stats.totalNodes }}</span></div>
          <div class="stat-item"><span class="stat-label">关系总数</span><span class="stat-value">{{ stats.totalEdges }}</span></div>
          <el-divider />
          <div class="stat-item"><span class="stat-label" style="color:#409eff">技能节点</span><span class="stat-value" style="color:#409eff">{{ stats.skillCount }}</span></div>
          <div class="stat-item"><span class="stat-label" style="color:#67c23a">岗位节点</span><span class="stat-value" style="color:#67c23a">{{ stats.jobCount }}</span></div>
          <div class="stat-item"><span class="stat-label" style="color:#e6a23c">领域节点</span><span class="stat-value" style="color:#e6a23c">{{ stats.domainCount }}</span></div>
          <el-divider />
          <div class="stat-item"><span class="stat-label">当前显示</span><span class="stat-value">{{ stats.displayed }} / {{ stats.totalNodes }}</span></div>
        </el-card>

        <el-card v-if="selectedNode" shadow="never" class="detail-card">
          <template #header>
            <div class="detail-header">
              <span>节点详情</span>
              <el-button text size="small" @click="selectedNode = null"><el-icon><Close /></el-icon></el-button>
            </div>
          </template>
          <div class="detail-body">
            <div class="detail-row"><span class="detail-label">名称</span><span class="detail-value">{{ selectedNode.label }}</span></div>
            <div class="detail-row">
              <span class="detail-label">类型</span>
              <el-tag :type="tagType(selectedNode.type)" size="small">{{ typeLabel(selectedNode.type) }}</el-tag>
            </div>
            <div class="detail-row"><span class="detail-label">关联数</span><span class="detail-value">{{ selectedNode.edgeCount }} 条关系</span></div>
            <div v-if="selectedNode.desc" class="detail-row desc-row">
              <span class="detail-label">描述</span>
              <span class="detail-value">{{ selectedNode.desc }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, shallowRef, onMounted, onUnmounted, nextTick } from 'vue'
import { Graph } from '@antv/g6'
import api from '../api'

let graph = null
const nodeType = ref('all')
const relType = ref('all')
const searchText = ref('')
const selectedNode = ref(null)
const loading = ref(false)
const hasData = ref(false)

let rawNodes = []
let rawEdges = []

const stats = ref({
  totalNodes: 0, totalEdges: 0,
  skillCount: 0, jobCount: 0, domainCount: 0,
  displayed: 0
})

function tagType(t) {
  const m = { domain: 'warning', skill: 'primary', job: 'success' }
  return m[t?.toLowerCase()] || 'info'
}
function typeLabel(t) {
  const m = { domain: '领域', skill: '技能', job: '岗位' }
  return m[t?.toLowerCase()] || '未知'
}
function nodeColor(t) {
  const m = { domain: '#e6a23c', skill: '#409eff', job: '#67c23a' }
  return m[t?.toLowerCase()] || '#909399'
}

async function fetchData() {
  loading.value = true
  try {
    const [jobsRes, skillsRes] = await Promise.allSettled([
      api.getJobs(),
      api.getSkills()
    ])

    let jobs = []
    if (jobsRes.status === 'fulfilled' && jobsRes.value) {
      const d = jobsRes.value
      jobs = d.data?.jobs || d.jobs || []
    }
    let skills = []
    if (skillsRes.status === 'fulfilled' && skillsRes.value) {
      const d = skillsRes.value
      skills = d.data?.skills || d.skills || []
    }

    const nodes = []
    const edges = []
    const domainSet = new Set()

    jobs.forEach((j, idx) => {
      const id = `j_${idx}`
      const domain = j.domain || j['j.domain'] || '未分类'
      nodes.push({
        id, type: 'job',
        label: j.title || `岗位${idx + 1}`,
        domain,
        desc: j.description || `${j.title} - ${domain}`
      })
      domainSet.add(domain)
    })

    skills.forEach((s, idx) => {
      const name = s.name || s.skill_name || s['s.name'] || ''
      if (!name) return
      const domain = s.domain || s['s.domain'] || ''
      nodes.push({
        id: `s_${idx}`, type: 'skill',
        label: name,
        domain,
        desc: name
      })
    })

    const domainList = Array.from(domainSet)
    domainList.forEach((d, idx) => {
      nodes.push({
        id: `d_${idx}`, type: 'domain',
        label: d, domain: d,
        desc: `${d}技术领域`
      })
    })

    jobs.forEach((j, jIdx) => {
      const domain = j.domain || j['j.domain'] || '未分类'
      const di = domainList.indexOf(domain)
      if (di >= 0) {
        edges.push({ source: `j_${jIdx}`, target: `d_${di}`, label: 'related' })
      }
    })

    rawNodes = nodes
    rawEdges = edges
    hasData.value = nodes.length > 0
    return nodes.length > 0
  } catch (e) {
    console.error('获取图谱数据失败:', e)
    rawNodes = []
    rawEdges = []
    hasData.value = false
    return false
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  let nodes = [...rawNodes]
  let edges = [...rawEdges]

  if (nodeType.value !== 'all') {
    nodes = nodes.filter(n => n.type === nodeType.value)
  }

  if (relType.value !== 'all') {
    edges = edges.filter(e => e.label === relType.value)
  }

  if (searchText.value.trim()) {
    const kw = searchText.value.trim().toLowerCase()
    const matched = new Set(
      nodes.filter(n => n.label.toLowerCase().includes(kw)).map(n => n.id)
    )
    nodes = nodes.filter(n => matched.has(n.id))
    edges = edges.filter(e => matched.has(e.source) && matched.has(e.target))
  }

  const validIds = new Set()
  edges.forEach(e => { validIds.add(e.source); validIds.add(e.target) })
  nodes = nodes.filter(n => validIds.has(n.id))

  return { nodes, edges }
}

function initGraph() {
  const el = document.getElementById('graph-container')
  if (!el) return

  if (graph) {
    try { graph.destroy() } catch (e) {}
    graph = null
  }

  const filtered = applyFilters()
  if (filtered.nodes.length === 0) return

  const data = {
    nodes: filtered.nodes.map(n => ({
      id: n.id,
      data: { type: n.type, label: n.label, domain: n.domain, desc: n.desc }
    })),
    edges: filtered.edges.map(e => ({
      source: e.source,
      target: e.target,
      data: { label: e.label }
    }))
  }

  try {
    graph = new Graph({
      container: 'graph-container',
      data,
      node: {
        style: (d) => {
          const t = d.data?.type || 'skill'
          const c = nodeColor(t)
          const sizes = { domain: 60, job: 50, skill: 40 }
          return {
            size: sizes[t] || 40,
            fill: c + '20',
            stroke: c,
            lineWidth: 2,
            labelText: d.data?.label || d.id,
            labelFontSize: t === 'domain' ? 13 : 11,
            labelFill: '#303133',
            labelOffsetY: t === 'domain' ? 34 : 28,
            labelPlacement: 'bottom'
          }
        }
      },
      edge: {
        style: {
          stroke: '#c0c4cc',
          lineWidth: 1.2,
          endArrow: true
        }
      },
      layout: {
        type: 'force',
        linkDistance: 150,
        preventOverlap: true,
        nodeStrength: -200,
        edgeStrength: 50,
        animation: false
      },
      behaviors: [
        { type: 'drag-canvas' },
        { type: 'zoom-canvas', sensitivity: 2 },
        { type: 'drag-element' }
      ],
      animation: false,
      autoFit: { type: 'view' }
    })

    graph.on('node:click', (event) => {
      const targetId = event.targetId
      const node = rawNodes.find(n => n.id === targetId)
      if (node) {
        const edgeCount = rawEdges.filter(e => e.source === targetId || e.target === targetId).length
        selectedNode.value = { ...node, edgeCount }
      }
    })
    graph.on('canvas:click', () => { selectedNode.value = null })

    graph.render()
    updateStats(filtered)
  } catch (e) {
    console.error('G6 初始化失败:', e)
  }
}

function updateStats(filtered) {
  stats.value = {
    totalNodes: rawNodes.length,
    totalEdges: rawEdges.length,
    skillCount: rawNodes.filter(n => n.type === 'skill').length,
    jobCount: rawNodes.filter(n => n.type === 'job').length,
    domainCount: rawNodes.filter(n => n.type === 'domain').length,
    displayed: filtered ? filtered.nodes.length : 0
  }
}

async function loadData() {
  await fetchData()
  await nextTick()
  initGraph()
}

function refreshGraph() {
  if (!rawNodes.length) return
  const filtered = applyFilters()
  if (graph) {
    const data = {
      nodes: filtered.nodes.map(n => ({
        id: n.id,
        data: { type: n.type, label: n.label, domain: n.domain, desc: n.desc }
      })),
      edges: filtered.edges.map(e => ({
        source: e.source,
        target: e.target,
        data: { label: e.label }
      }))
    }
    try {
      graph.setData(data)
      graph.render()
    } catch (e) {
      initGraph()
    }
  } else {
    initGraph()
  }
  updateStats(filtered)
}

function onSearch() {
  refreshGraph()
}

function zoomIn() {
  if (graph) graph.zoomTo({ mode: 'relative', value: 1.2 })
}
function zoomOut() {
  if (graph) graph.zoomTo({ mode: 'relative', value: 0.8 })
}
function fitView() {
  if (graph) graph.fitView()
}

async function initDefault() {
  try {
    await api.initializeGraph()
    await loadData()
  } catch (e) {
    console.error('初始化失败:', e)
  }
}

onMounted(() => { loadData() })
onUnmounted(() => {
  if (graph) {
    try { graph.destroy() } catch (e) {}
    graph = null
  }
})
</script>

<style scoped>
.graph-card { border-radius: 8px; border: 1px solid var(--border-color); min-height: 600px; }
.graph-toolbar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.toolbar-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.toolbar-right { display: flex; gap: 6px; }
.graph-container { width: 100%; height: 620px; border-radius: 4px; background: #fafafa; display: flex; align-items: center; justify-content: center; position: relative; }
.empty-hint { text-align: center; color: var(--text-muted); }
.empty-hint p { margin: 8px 0 4px; font-size: 14px; }
.empty-sub { font-size: 13px !important; color: var(--text-secondary) !important; }
.stats-card { border-radius: 8px; border: 1px solid var(--border-color); margin-bottom: 16px; }
.stat-item { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; }
.stat-label { font-size: 13px; color: var(--text-secondary); }
.stat-value { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.detail-card { border-radius: 8px; border: 1px solid var(--border-color); }
.detail-header { display: flex; justify-content: space-between; align-items: center; }
.detail-body { display: flex; flex-direction: column; gap: 10px; }
.detail-row { display: flex; flex-direction: column; gap: 2px; }
.detail-label { font-size: 12px; color: var(--text-muted); }
.detail-value { font-size: 14px; color: var(--text-primary); font-weight: 500; }
.desc-row .detail-value { font-size: 13px; font-weight: 400; color: var(--text-secondary); line-height: 1.5; }
</style>
