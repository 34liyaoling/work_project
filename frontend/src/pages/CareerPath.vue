<template>
  <div class="page-container">
    <div class="page-header">
      <h2>职业路径</h2>
      <p>基于知识图谱与市场趋势，智能生成多元化职业发展路径规划</p>
    </div>

    <el-card shadow="never" class="param-card">
      <el-row :gutter="16" align="middle">
        <el-col :span="8">
          <div class="param-item">
            <label class="param-label">起始角色</label>
            <el-autocomplete
              v-model="startRole"
              :fetch-suggestions="queryJobSuggestions"
              placeholder="输入或选择当前职位"
              style="width: 100%"
              clearable
              :trigger-on-focus="true"
            />
          </div>
        </el-col>
        <el-col :span="2">
          <el-button type="primary" size="large" style="width: 100%; margin-top: 22px;" :loading="generating" @click="generatePath">
            生成路径
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <template v-if="pathData.length > 0">
      <div class="path-overview">
        <div class="section-title">职业路径全景</div>
        <el-card shadow="never" class="chart-card">
          <div ref="pathChartRef" class="path-chart"></div>
        </el-card>
      </div>

      <div class="path-cards">
        <el-row :gutter="16">
          <el-col :span="8" v-for="(path, pIdx) in pathData" :key="pIdx">
            <el-card
              shadow="never"
              :class="['path-card', pathClass(path.type)]"
            >
              <template #header>
                <div class="path-card-header">
                  <el-tag :type="pathTagType(path.type)" size="small" effect="dark">{{ path.label }}</el-tag>
                  <span class="path-difficulty">{{ path.difficulty }}</span>
                </div>
              </template>
              <div class="path-steps">
                <div
                  v-for="(step, sIdx) in path.steps"
                  :key="sIdx"
                  class="path-step"
                  @click="selectedStep = { pathIdx: pIdx, stepIdx: sIdx, step }"
                >
                  <div class="step-index">{{ sIdx + 1 }}</div>
                  <div class="step-content">
                    <div class="step-title">{{ step.title }}</div>
                    <div class="step-meta">
                      <span>{{ step.duration }}</span>
                      <el-tag
                        v-if="step.skillCount"
                        size="small"
                        type="info"
                        style="margin-left: 6px;"
                      >{{ step.skillCount }} 技能</el-tag>
                    </div>
                    <el-progress
                      v-if="step.matchRate"
                      :percentage="step.matchRate"
                      :stroke-width="6"
                      :color="matchRateColor(step.matchRate)"
                      :format="() => step.matchRate + '%'"
                    />
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <el-dialog
        v-model="dialogVisible"
        :title="selectedStep?.step?.title || '节点详情'"
        width="500px"
      >
        <template v-if="selectedStep">
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="所属路径">
              <el-tag :type="pathTagType(pathData[selectedStep.pathIdx]?.type)" size="small">
                {{ pathData[selectedStep.pathIdx]?.label }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="阶段">{{ selectedStep.step.stage || '--' }}</el-descriptions-item>
            <el-descriptions-item label="建议时长">{{ selectedStep.step.duration }}</el-descriptions-item>
            <el-descriptions-item label="所需技能" v-if="selectedStep.step.skills">
              <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                <el-tag v-for="s in selectedStep.step.skills" :key="s" size="small" type="primary">{{ s }}</el-tag>
              </div>
            </el-descriptions-item>
            <el-descriptions-item label="描述" v-if="selectedStep.step.description">
              {{ selectedStep.step.description }}
            </el-descriptions-item>
          </el-descriptions>
          <div v-if="selectedStep.step.suggestions" style="margin-top: 12px; padding: 12px; background: #fafafa; border-radius: 6px;">
            <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.6;">{{ selectedStep.step.suggestions }}</p>
          </div>
        </template>
      </el-dialog>

      <el-card shadow="never" class="table-card">
        <template #header>
          <div class="card-header">
            <span>路径步骤详情</span>
            <el-tag type="info" size="small">{{ flatSteps.length }} 个阶段</el-tag>
          </div>
        </template>
        <el-table :data="flatSteps" stripe style="width: 100%" size="small" @row-click="onTableRowClick">
          <el-table-column prop="pathLabel" label="路径" width="110">
            <template #default="{ row }">
              <el-tag :type="pathTagType(row.pathType)" size="small">{{ row.pathLabel }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column type="index" label="阶段" width="60" />
          <el-table-column prop="title" label="阶段名称" min-width="130" />
          <el-table-column prop="duration" label="时长" width="80" />
          <el-table-column prop="matchRate" label="匹配率" width="80" sortable>
            <template #default="{ row }">
              <el-progress :percentage="row.matchRate" :stroke-width="10" :color="matchRateColor(row.matchRate)" :format="() => row.matchRate + '%'" />
            </template>
          </el-table-column>
          <el-table-column prop="skillCount" label="技能数" width="70" sortable />
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        </el-table>
      </el-card>
    </template>

    <div v-if="!generating && pathData.length === 0" class="empty-state">
      <el-icon><Guide /></el-icon>
      <p>输入起始角色后点击「生成路径」查看职业发展路径规划</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '../api'

const startRole = ref('')
const generating = ref(false)
const pathData = ref([])
const dialogVisible = ref(false)
const selectedStep = ref(null)

const pathChartRef = ref(null)
let pathChart = null

const jobList = ref([])

const flatSteps = computed(() => {
  const result = []
  pathData.value.forEach((path) => {
    path.steps.forEach((step) => {
      result.push({
        ...step,
        pathLabel: path.label,
        pathType: path.type
      })
    })
  })
  return result
})

function pathClass(type) {
  switch (type) {
    case 'expert': return 'path-expert'
    case 'ai': return 'path-ai'
    case 'management': return 'path-management'
    default: return ''
  }
}

function pathTagType(type) {
  switch (type) {
    case 'expert': return 'primary'
    case 'ai': return 'warning'
    case 'management': return 'success'
    default: return 'info'
  }
}

function matchRateColor(percentage) {
  if (percentage >= 80) return '#67c23a'
  if (percentage >= 60) return '#e6a23c'
  return '#f56c6c'
}

function queryJobSuggestions(query, cb) {
  const results = query
    ? jobList.value.filter(j => (j.title || j).includes(query))
    : jobList.value
  cb(results.map(j => ({ value: j.title || j })))
}

async function generatePath() {
  if (!startRole.value) return
  generating.value = true
  try {
    const res = await api.planCareer({ current_role: startRole.value })
    pathData.value = res?.paths || res || []
  } catch (e) {
    console.error('生成职业路径失败:', e)
    pathData.value = []
  }
  generating.value = false
  await nextTick()
  initPathChart()
}

function initPathChart() {
  if (!pathChartRef.value || pathData.value.length === 0) return
  if (pathChart) pathChart.dispose()
  pathChart = echarts.init(pathChartRef.value)

  const colors = ['#409eff', '#e6a23c', '#67c23a']
  const pathLabels = ['技术专家路线', 'AI转型路线', '管理路线']

  const series = pathData.value.map((path, pIdx) => {
    const data = path.steps.map((step, sIdx) => ({
      value: [sIdx, step.matchRate, pIdx],
      name: step.title,
      pathLabel: path.label,
      matchRate: step.matchRate,
      duration: step.duration,
      description: step.description
    }))
    return {
      name: pathLabels[pIdx],
      type: 'scatter',
      data: data,
      symbolSize: (val) => 16 + (val[1] / 100) * 20,
      itemStyle: {
        color: colors[pIdx],
        shadowBlur: 6,
        shadowColor: colors[pIdx] + '60'
      },
      label: {
        show: true,
        formatter: (params) => params.data.name,
        position: 'top',
        fontSize: 11,
        color: '#303133',
        fontWeight: 500
      },
      connectLines: {
        show: true,
        lineStyle: {
          color: colors[pIdx],
          width: 2,
          type: 'solid',
          opacity: 0.5
        }
      }
    }
  })

  pathChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        const d = params.data
        return `<strong>${d.name}</strong><br/>
          <span>路径: ${d.pathLabel}</span><br/>
          <span>匹配率: ${d.matchRate}%</span><br/>
          <span>时长: ${d.duration}</span><br/>
          <span style="font-size:12px;color:#909399;">${d.description || ''}</span>`
      }
    },
    grid: {
      left: '3%',
      right: '8%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['阶段一', '阶段二', '阶段三', '阶段四'],
      axisLabel: { fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      name: '匹配率 %',
      min: 30,
      max: 100,
      axisLabel: { formatter: '{value}%' }
    },
    series: series,
    legend: {
      data: pathLabels,
      bottom: 0,
      left: 'center',
      textStyle: { fontSize: 12 }
    }
  })

  pathChart.on('click', (params) => {
    const pIdx = pathData.value.findIndex(p => p.label === params.data.pathLabel)
    const sIdx = pathData.value[pIdx]?.steps.findIndex(s => s.title === params.data.name)
    if (pIdx >= 0 && sIdx >= 0) {
      selectedStep.value = { pathIdx: pIdx, stepIdx: sIdx, step: pathData.value[pIdx].steps[sIdx] }
      dialogVisible.value = true
    }
  })
}

function onTableRowClick(row) {
  const pIdx = pathData.value.findIndex(p => p.label === row.pathLabel)
  const sIdx = pathData.value[pIdx]?.steps.findIndex(s => s.title === row.title)
  if (pIdx >= 0 && sIdx >= 0) {
    selectedStep.value = { pathIdx: pIdx, stepIdx: sIdx, step: pathData.value[pIdx].steps[sIdx] }
    dialogVisible.value = true
  }
}

function handleResize() {
  pathChart?.resize()
}

onMounted(async () => {
  try {
    const jobs = await api.getJobs()
    if (Array.isArray(jobs)) {
      jobList.value = jobs
    } else if (jobs?.jobs) {
      jobList.value = jobs.jobs
    }
  } catch (e) {
    console.error('获取职位列表失败:', e)
  }
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  pathChart?.dispose()
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

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.path-overview {
  margin-bottom: 24px;
}

.path-chart {
  width: 100%;
  height: 380px;
}

.chart-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.path-cards {
  margin-bottom: 24px;
}

.path-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
  height: 100%;
}

.path-card.path-expert {
  border-top: 3px solid #409eff;
}

.path-card.path-ai {
  border-top: 3px solid #e6a23c;
}

.path-card.path-management {
  border-top: 3px solid #67c23a;
}

.path-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.path-difficulty {
  font-size: 12px;
  color: var(--text-muted);
}

.path-steps {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.path-step {
  display: flex;
  gap: 12px;
  padding: 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.path-step:hover {
  background: #f5f7fa;
}

.step-index {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--bg-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 2px;
}

.step-meta {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
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
</style>
