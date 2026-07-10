<template>
  <div class="page-container">
    <div class="page-header">
      <h2>智能匹配</h2>
      <p>基于混合匹配引擎（图谱推理 + 向量检索 + LLM排序），精准匹配最优岗位</p>
    </div>

    <el-card shadow="never" class="param-card">
      <el-row :gutter="24">
        <el-col :span="8">
          <div class="param-item">
            <label class="param-label">选择简历</label>
            <el-select v-model="selectedResume" placeholder="请先上传简历" style="width: 100%" clearable>
              <el-option
                v-for="r in resumeList"
                :key="r.id"
                :label="r.name"
                :value="r.id"
              />
            </el-select>
            <div v-if="resumeList.length === 0" class="param-hint">
              暂无简历，请先在「简历分析」页面上传
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="param-item">
            <label class="param-label">匹配数量：{{ matchCount }}</label>
            <el-slider v-model="matchCount" :min="3" :max="20" :step="1" show-stops :marks="{3:'3',10:'10',20:'20'}" />
          </div>
        </el-col>
        <el-col :span="6">
          <div class="param-item">
            <label class="param-label">领域筛选</label>
            <el-select v-model="selectedDomain" placeholder="全部领域" style="width: 100%" clearable>
              <el-option
                v-for="d in domainList"
                :key="d"
                :label="d"
                :value="d"
              />
            </el-select>
          </div>
        </el-col>
        <el-col :span="2" style="display: flex; align-items: flex-end;">
          <el-button type="primary" size="large" style="width: 100%" :loading="matching" @click="startMatch">
            开始匹配
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <template v-if="matchResults.length > 0">
      <div class="best-match-section">
        <div class="section-title">
          <el-tag type="danger" size="small" effect="dark">最佳推荐</el-tag>
          <span>最高匹配岗位</span>
        </div>
        <el-card shadow="never" class="best-match-card">
          <el-row :gutter="24">
            <el-col :span="14">
              <div class="best-match-info">
                <h3>{{ bestMatch.jobTitle }}</h3>
                <div class="best-match-meta">
                  <el-tag>{{ bestMatch.domain }}</el-tag>
                  <span class="meta-item">综合匹配度</span>
                </div>
                <div class="dimension-bars">
                  <div v-for="dim in bestMatch.dimensions" :key="dim.name" class="dim-row">
                    <span class="dim-name">{{ dim.name }}</span>
                    <el-progress
                      :percentage="dim.score"
                      :color="dimColor(dim.score)"
                      :stroke-width="14"
                      :format="() => dim.score + '分'"
                    />
                  </div>
                </div>
                <el-button type="primary" link @click="showBestDetail = !showBestDetail">
                  {{ showBestDetail ? '收起详情' : '查看详情' }}
                </el-button>
                <el-collapse-transition>
                  <div v-if="showBestDetail" class="best-detail">
                    <p>{{ bestMatch.explanation }}</p>
                  </div>
                </el-collapse-transition>
              </div>
            </el-col>
            <el-col :span="10">
              <div ref="bestChartRef" class="best-chart"></div>
            </el-col>
          </el-row>
        </el-card>
      </div>

      <el-card shadow="never" class="table-card">
        <template #header>
          <div class="card-header">
            <span>全部匹配结果</span>
            <el-tag type="info" size="small">{{ matchResults.length }} 个匹配</el-tag>
          </div>
        </template>
        <el-table :data="matchResults" stripe style="width: 100%" size="small" @expand-change="onExpandChange">
          <el-table-column type="expand" width="40">
            <template #default="{ row }">
              <div class="expand-detail">
                <h4>匹配解释</h4>
                <p>{{ row.explanation }}</p>
                <div v-if="row.pathDetail" style="margin-top: 12px;">
                  <h4>图谱路径</h4>
                  <p>{{ row.pathDetail }}</p>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="jobTitle" label="岗位名称" min-width="160" />
          <el-table-column prop="totalScore" label="总分数" width="90" sortable>
            <template #default="{ row }">
              <span :style="{ color: scoreColor(row.totalScore), fontWeight: 600 }">{{ row.totalScore }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="skillMatch" label="技能匹配" width="90" sortable>
            <template #default="{ row }">
              <el-tag :type="scoreTagType(row.skillMatch)" size="small">{{ row.skillMatch }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="graphMatch" label="图路径匹配" width="100" sortable>
            <template #default="{ row }">
              <el-tag :type="scoreTagType(row.graphMatch)" size="small">{{ row.graphMatch }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="vectorMatch" label="向量匹配" width="90" sortable>
            <template #default="{ row }">
              <el-tag :type="scoreTagType(row.vectorMatch)" size="small">{{ row.vectorMatch }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="trendBonus" label="趋势加分" width="90" sortable>
            <template #default="{ row }">
              <el-tag type="success" size="small" v-if="row.trendBonus > 0">+{{ row.trendBonus }}</el-tag>
              <span v-else class="text-muted">--</span>
            </template>
          </el-table-column>
          <el-table-column prop="credibility" label="可信度" width="80" sortable>
            <template #default="{ row }">
              <el-progress :percentage="row.credibility" :stroke-width="10" :show-text="false" />
              <span style="font-size: 11px; color: var(--text-muted);">{{ row.credibility }}%</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <div v-if="!matching && matchResults.length === 0" class="empty-state">
      <el-icon><Connection /></el-icon>
      <p>设置参数后点击「开始匹配」查看匹配结果</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import api from '../api'
import { useResumeStore } from '../stores/resume'

const router = useRouter()
const resumeStore = useResumeStore()

const selectedResume = ref('')
const matchCount = ref(10)
const selectedDomain = ref('')
const matching = ref(false)
const matchResults = ref([])
const showBestDetail = ref(false)

const bestChartRef = ref(null)
let bestChart = null

const resumeList = ref([])
const domainList = ref(['人工智能', '前端开发', '后端开发', 'DevOps', '大数据', '网络安全', '移动端', '区块链'])

const bestMatch = computed(() => matchResults.value[0] || {})

function dimColor(score) {
  if (score >= 85) return '#67c23a'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
}

function scoreColor(score) {
  if (score >= 85) return '#67c23a'
  if (score >= 70) return '#409eff'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
}

function scoreTagType(score) {
  if (score >= 85) return 'success'
  if (score >= 70) return 'primary'
  if (score >= 60) return 'warning'
  return 'danger'
}

async function startMatch() {
  matching.value = true
  try {
    // 优先用 store 里的 resume_id（从简历分析页带来的）
    const resumeId = selectedResume.value || resumeStore.resumeId || undefined
    const params = {
      resume_id: resumeId,
      top_n: matchCount.value,
    }
    const res = await api.match(params)
    // 后端返回 {success, data: {matches: [...]}}
    const matches = res?.data?.matches || res?.matches || (Array.isArray(res) ? res : [])
    matchResults.value = matches
  } catch (error) {
    console.error('匹配请求失败:', error.message)
    matchResults.value = []
  }
  matching.value = false
  await nextTick()
  initBestChart()
}

function onExpandChange(row) {
  console.log('展开详情:', row.jobTitle)
}

function goToGapAnalysis(jobTitle) {
  router.push({ name: 'GapAnalysis', query: { target_job: jobTitle } })
}

function initBestChart() {
  if (!bestChartRef.value || !bestMatch.value.dimensions) return
  if (bestChart) bestChart.dispose()
  bestChart = echarts.init(bestChartRef.value)
  const dims = bestMatch.value.dimensions
  bestChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dims.map(d => d.name),
      axisLabel: { fontSize: 11 }
    },
    yAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}分' } },
    series: [{
      type: 'bar',
      data: dims.map(d => ({
        value: d.score,
        itemStyle: {
          color: dimColor(d.score),
          borderRadius: [4, 4, 0, 0]
        }
      })),
      barWidth: '50%',
      label: {
        show: true,
        position: 'top',
        formatter: '{c}',
        fontSize: 11,
        fontWeight: 600
      }
    }]
  })
}

function handleResize() {
  bestChart?.resize()
}

onMounted(async () => {
  // 从简历分析页带过来的 resume_id，自动填入
  if (resumeStore.resumeId) {
    selectedResume.value = resumeStore.resumeId
    ElMessage.info(`已自动带入简历：${resumeStore.candidateName || resumeStore.resumeId}`)
  }
  try {
    const jobs = await api.getJobs()
    if (Array.isArray(jobs)) {
      const domains = [...new Set(jobs.map(j => j.domain || j.category).filter(Boolean))]
      if (domains.length > 0) domainList.value = domains
    }
  } catch {
    // use default domain list
  }
  try {
    const skills = await api.getSkills()
    if (Array.isArray(skills)) {
      // derive domains from skills if available
    }
  } catch {
    // ignore
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  bestChart?.dispose()
})
</script>

<style scoped>
.param-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
  margin-bottom: 24px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.param-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.param-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.best-match-section {
  margin-bottom: 24px;
}

.best-match-card {
  border-radius: 8px;
  border: 2px solid #f56c6c40;
  background: linear-gradient(135deg, #fef0f0 0%, #fff 50%);
}

.best-match-info h3 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.best-match-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.meta-item {
  font-size: 13px;
  color: var(--text-secondary);
}

.dimension-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.dim-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dim-name {
  font-size: 12px;
  color: var(--text-secondary);
  width: 72px;
  flex-shrink: 0;
  text-align: right;
}

.dim-row .el-progress {
  flex: 1;
}

.best-detail {
  margin-top: 12px;
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.best-chart {
  width: 100%;
  height: 220px;
}

.table-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 15px;
}

.expand-detail {
  padding: 16px 24px;
}

.expand-detail h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.expand-detail p {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.text-muted {
  color: var(--text-muted);
  font-size: 12px;
}
</style>
