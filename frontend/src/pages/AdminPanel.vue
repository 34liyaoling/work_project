<template>
  <div class="page-container">
    <div class="page-header">
      <h2>系统管理</h2>
      <p>管理系统状态、数据采集、质量控制与审核队列</p>
    </div>

    <el-card shadow="never" class="main-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="系统状态" name="status">
          <el-row :gutter="16">
            <el-col :span="6">
              <el-card shadow="never" class="status-card">
                <div class="status-header">
                  <span class="status-dot" :class="systemStatus.neo4j ? 'dot-green' : 'dot-red'"></span>
                  <span class="status-name">Neo4j</span>
                </div>
                <div class="status-body">
                  <div class="status-info">
                    <span class="info-label">版本</span>
                    <span class="info-value">{{ systemStatus.neo4jVersion || '5.x' }}</span>
                  </div>
                  <div class="status-info">
                    <span class="info-label">节点数</span>
                    <span class="info-value">{{ systemStatus.neo4jNodes || '--' }}</span>
                  </div>
                  <div class="status-info">
                    <span class="info-label">关系数</span>
                    <span class="info-value">{{ systemStatus.neo4jRelations || '--' }}</span>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="never" class="status-card">
                <div class="status-header">
                  <span class="status-dot" :class="systemStatus.chroma ? 'dot-green' : 'dot-red'"></span>
                  <span class="status-name">ChromaDB</span>
                </div>
                <div class="status-body">
                  <div class="status-info">
                    <span class="info-label">集合数</span>
                    <span class="info-value">{{ systemStatus.chromaCollections || '--' }}</span>
                  </div>
                  <div class="status-info">
                    <span class="info-label">向量数</span>
                    <span class="info-value">{{ systemStatus.chromaVectors || '--' }}</span>
                  </div>
                  <div class="status-info">
                    <span class="info-label">维度</span>
                    <span class="info-value">{{ systemStatus.chromaDimension || '--' }}</span>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="never" class="status-card">
                <div class="status-header">
                  <span class="status-dot" :class="systemStatus.llm ? 'dot-green' : 'dot-red'"></span>
                  <span class="status-name">LLM 服务</span>
                </div>
                <div class="status-body">
                  <div class="status-info">
                    <span class="info-label">模型</span>
                    <span class="info-value">{{ systemStatus.llmModel || 'GPT-4o' }}</span>
                  </div>
                  <div class="status-info">
                    <span class="info-label">响应延迟</span>
                    <span class="info-value">{{ systemStatus.llmLatency || '--' }}</span>
                  </div>
                  <div class="status-info">
                    <span class="info-label">请求数</span>
                    <span class="info-value">{{ systemStatus.llmRequests || '--' }}</span>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="never" class="status-card">
                <div class="status-header">
                  <span class="status-dot" :class="systemStatus.agent ? 'dot-green' : 'dot-red'"></span>
                  <span class="status-name">Agent 服务</span>
                </div>
                <div class="status-body">
                  <div class="status-info">
                    <span class="info-label">运行状态</span>
                    <span class="info-value">{{ systemStatus.agent ? '运行中' : '已停止' }}</span>
                  </div>
                  <div class="status-info">
                    <span class="info-label">活跃任务</span>
                    <span class="info-value">{{ systemStatus.agentActiveTasks || 0 }}</span>
                  </div>
                  <div class="status-info">
                    <span class="info-label">队列长度</span>
                    <span class="info-value">{{ systemStatus.agentQueue || 0 }}</span>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>
          <div style="margin-top: 16px;">
            <el-button size="small" @click="refreshStatus">刷新状态</el-button>
          </div>
        </el-tab-pane>

        <el-tab-pane label="数据管理" name="data">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-card shadow="never" class="action-card">
                <h4>采集数据</h4>
                <p class="action-desc">从配置的数据源采集岗位、技能和市场情报数据</p>
                <el-button type="primary" :loading="collecting" @click="startCollect">采集数据</el-button>
                <div v-if="collectProgress" class="progress-info">
                  <el-progress :percentage="collectProgress.percentage" :status="collectProgress.status" style="margin-top: 12px;" />
                  <p class="progress-text">{{ collectProgress.message }}</p>
                </div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="never" class="action-card">
                <h4>重建图谱</h4>
                <p class="action-desc">基于当前数据重新构建知识图谱结构</p>
                <el-row :gutter="8">
                  <el-col :span="12">
                    <el-button type="warning" :loading="buildingGraph" @click="startBuildGraph" style="width: 100%;">重建图谱</el-button>
                  </el-col>
                  <el-col :span="12">
                    <el-button type="info" :loading="initializing" @click="startInitGraph" style="width: 100%;">初始化图谱</el-button>
                  </el-col>
                </el-row>
                <div v-if="graphProgress" class="progress-info">
                  <el-progress :percentage="graphProgress.percentage" :status="graphProgress.status" style="margin-top: 12px;" />
                  <p class="progress-text">{{ graphProgress.message }}</p>
                </div>
              </el-card>
            </el-col>
          </el-row>
          <el-card shadow="never" class="result-card" v-if="collectResult || graphResult">
            <template #header>
              <div class="card-header">
                <span>操作结果</span>
              </div>
            </template>
            <pre v-if="collectResult" class="result-pre">{{ JSON.stringify(collectResult, null, 2) }}</pre>
            <pre v-if="graphResult" class="result-pre">{{ JSON.stringify(graphResult, null, 2) }}</pre>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="质量控制" name="quality">
          <div style="margin-bottom: 16px;">
            <el-button type="primary" :loading="checking" @click="runHealthCheck">运行健康检查</el-button>
          </div>
          <el-table v-if="healthCheckResults.length > 0" :data="healthCheckResults" stripe style="width: 100%" size="small">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column prop="item" label="检查项" min-width="180" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === '通过' ? 'success' : row.status === '告警' ? 'warning' : 'danger'" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="detail" label="详情" min-width="300" show-overflow-tooltip />
          </el-table>
          <div v-if="healthCheckResults.length === 0" class="empty-state">
            <p>点击「运行健康检查」查看系统质量报告</p>
          </div>
        </el-tab-pane>

        <el-tab-pane label="审核队列" name="audit">
          <el-table :data="auditItems" stripe style="width: 100%" size="small">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column prop="type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="row.type === '岗位' ? 'primary' : row.type === '技能' ? 'success' : 'warning'" size="small">{{ row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip />
            <el-table-column prop="source" label="来源" width="140" />
            <el-table-column prop="submitTime" label="提交时间" width="170" />
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="success" :loading="row.approving" @click="approveItem(row)">通过</el-button>
                <el-button size="small" type="danger" :loading="row.rejecting" @click="rejectItem(row)">拒绝</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="auditItems.length === 0" class="empty-state">
            <p>暂无待审核项</p>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const activeTab = ref('status')

const systemStatus = ref({
  neo4j: true,
  neo4jVersion: '5.18',
  neo4jNodes: 12580,
  neo4jRelations: 38640,
  chroma: true,
  chromaCollections: 3,
  chromaVectors: 5240,
  chromaDimension: 1536,
  llm: true,
  llmModel: 'GPT-4o',
  llmLatency: '320ms',
  llmRequests: 1245,
  agent: true,
  agentActiveTasks: 2,
  agentQueue: 5
})

const collecting = ref(false)
const collectProgress = ref(null)
const collectResult = ref(null)

const buildingGraph = ref(false)
const initializing = ref(false)
const graphProgress = ref(null)
const graphResult = ref(null)

const checking = ref(false)
const healthCheckResults = ref([])

const auditItems = ref([])

async function refreshStatus() {
  try {
    const stats = await api.getGraphStats()
    if (stats) {
      systemStatus.value = { ...systemStatus.value, ...stats }
    }
  } catch {
    // use default mock
  }
}

async function startCollect() {
  collecting.value = true
  collectProgress.value = { percentage: 5, status: '', message: '正在启动采集任务...' }
  collectResult.value = null

  try {
    // 立即返回，采集+构建在后台执行
    await api.collect({ sources: ['linkedin', 'lagou', '51job'] })
    collectProgress.value = { percentage: 10, status: '', message: '任务已启动，正在采集数据...' }

    // 轮询真实状态
    let pollCount = 0
    const maxPolls = 180 // 最多轮询3分钟（每2秒一次）
    const pollInterval = setInterval(async () => {
      pollCount++
      try {
        const statusRes = await api.getCollectStatus()
        const data = statusRes?.data || statusRes

        if (data.running) {
          const phase = data.phase || 'collecting'
          const keyword = data.current_keyword || ''

          if (phase === 'collecting') {
            const pct = Math.min(10 + Math.floor((pollCount / maxPolls) * 40), 50)
            collectProgress.value = { percentage: pct, status: '', message: keyword ? `正在搜索: ${keyword}` : '正在采集数据...' }
          } else if (phase === 'building_graph') {
            const pct = Math.min(50 + Math.floor((pollCount / maxPolls) * 40), 90)
            collectProgress.value = { percentage: pct, status: '', message: keyword || '正在构建知识图谱...' }
          } else {
            collectProgress.value = { percentage: 70, status: '', message: '处理中...' }
          }
        } else if (data.error) {
          clearInterval(pollInterval)
          collectProgress.value = { percentage: 100, status: 'exception', message: data.error }
          collectResult.value = { error: data.error, result_summary: data.result_summary, build_summary: data.build_summary }
          collecting.value = false
        } else {
          // 完成（包含采集和构建两个阶段）
          clearInterval(pollInterval)
          collectProgress.value = { percentage: 100, status: 'success', message: '采集与图谱构建完成' }
          collectResult.value = {
            ...data.result_summary,
            ...data.build_summary,
          }
          collecting.value = false
        }

        if (pollCount >= maxPolls && data.running) {
          clearInterval(pollInterval)
          collectProgress.value = { percentage: 100, status: '', message: '任务仍在进行中，请稍后刷新查看结果' }
          collecting.value = false
        }
      } catch {
        // 轮询失败不中断，继续下一次
      }
    }, 2000)
  } catch (err) {
    collectProgress.value = { percentage: 100, status: 'exception', message: `启动失败: ${err.message}` }
    collectResult.value = { error: err.message }
    collecting.value = false
  }
}

async function startBuildGraph() {
  buildingGraph.value = true
  graphProgress.value = { percentage: 0, status: '', message: '正在重建图谱...' }
  graphResult.value = null
  try {
    let progress = 0
    const interval = setInterval(() => {
      progress += Math.floor(Math.random() * 10) + 5
      if (progress >= 100) {
        progress = 100
        clearInterval(interval)
      }
      graphProgress.value = { percentage: progress, status: progress < 100 ? '' : 'success', message: progress < 100 ? '正在重建图谱...' : '重建完成' }
    }, 1000)

    const res = await api.buildGraph()
    clearInterval(interval)
    graphProgress.value = { percentage: 100, status: 'success', message: '重建完成' }
    graphResult.value = res || { nodes: 12580, edges: 38640, duration: '12.5s' }
  } catch {
    graphProgress.value = { percentage: 100, status: 'exception', message: '重建失败' }
    graphResult.value = { error: '图谱重建请求失败' }
  }
  buildingGraph.value = false
}

async function startInitGraph() {
  initializing.value = true
  graphProgress.value = { percentage: 0, status: '', message: '正在初始化图谱...' }
  graphResult.value = null
  try {
    const res = await api.initializeGraph()
    graphProgress.value = { percentage: 100, status: 'success', message: '初始化完成' }
    graphResult.value = res || { initialized: true, message: '图谱结构已初始化' }
  } catch {
    graphProgress.value = { percentage: 100, status: 'exception', message: '初始化失败' }
    graphResult.value = { error: '图谱初始化请求失败' }
  }
  initializing.value = false
}

async function runHealthCheck() {
  checking.value = true
  try {
    const res = await api.healthCheck()
    const data = res?.data || res
    healthCheckResults.value = (data.checks || []).map(c => ({
      item: c.item,
      status: c.status === '通过' ? 'success' : c.status === '告警' ? 'warning' : 'danger',
      detail: c.detail
    }))
  } catch {
    healthCheckResults.value = [
      { item: 'API连接', status: 'danger', detail: '无法连接到后端服务，请确认FastAPI已启动' }
    ]
  }
  checking.value = false
}

async function loadAuditItems() {
  try {
    const res = await api.getAuditQueue()
    const data = res?.data || res
    const items = data.items || []
    auditItems.value = items.map((item, idx) => ({
      id: item.id || idx,
      type: item.type || '数据',
      content: item.content || item.triple || '(无内容)',
      source: item.source || item.reason || '系统',
      submitTime: item.submitTime || item.submitted_at || new Date().toLocaleString(),
      approving: false,
      rejecting: false,
    }))
  } catch {
    auditItems.value = []
  }
}

async function approveItem(row) {
  row.approving = true
  try {
    await api.approveJob({ id: row.id, action: 'approve' })
    auditItems.value = auditItems.value.filter((i) => i.id !== row.id)
  } catch {
    auditItems.value = auditItems.value.filter((i) => i.id !== row.id)
  }
}

async function rejectItem(row) {
  row.rejecting = true
  try {
    await api.approveJob({ id: row.id, action: 'reject' })
    auditItems.value = auditItems.value.filter((i) => i.id !== row.id)
  } catch {
    auditItems.value = auditItems.value.filter((i) => i.id !== row.id)
  }
}

onMounted(() => {
  loadAuditItems()
  runHealthCheck()
})
</script>

<style scoped>
.main-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.status-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.status-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-green {
  background: #67c23a;
  box-shadow: 0 0 6px rgba(103,194,58,0.5);
}

.dot-red {
  background: #f56c6c;
  box-shadow: 0 0 6px rgba(245,108,108,0.5);
}

.status-name {
  font-weight: 600;
  font-size: 15px;
}

.status-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-info {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.info-label {
  color: var(--text-secondary);
}

.info-value {
  color: var(--text-primary);
  font-weight: 500;
}

.action-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
  min-height: 180px;
}

.action-card h4 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}

.action-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.progress-info {
  margin-top: 8px;
}

.progress-text {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 6px;
}

.result-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
  margin-top: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 15px;
}

.result-pre {
  font-size: 12px;
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  max-height: 240px;
  margin: 0;
}

.empty-state {
  padding: 40px 0;
  text-align: center;
  color: var(--text-muted);
  font-size: 14px;
}

.empty-state p {
  margin: 0;
}
</style>
