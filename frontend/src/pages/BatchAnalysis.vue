<template>
  <div class="page-container">
    <div class="page-header">
      <h2>批量分析</h2>
      <p>批量上传简历，进行团队技能覆盖度分析与能力评估</p>
    </div>

    <el-card v-if="!analysisDone" shadow="never" class="upload-card">
      <div class="upload-area">
        <el-upload
          ref="uploadRef"
          drag
          multiple
          accept=".pdf,.docx,.doc,.txt"
          :file-list="fileList"
          :auto-upload="false"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
        >
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="upload-text">
            <span>拖拽多份简历文件到此处，或 <em>点击选择</em></span>
          </div>
          <template #tip>
            <div class="upload-tip">
              支持 PDF、DOCX、TXT 格式，可同时选择多份文件
            </div>
          </template>
        </el-upload>
      </div>
      <div v-if="fileList.length > 0" class="file-count-info">
        已选择 <strong>{{ fileList.length }}</strong> 份简历
      </div>
      <div class="upload-actions">
        <el-button type="primary" size="large" :loading="analyzing" :disabled="fileList.length === 0" @click="startBatchAnalysis">
          开始批量分析
        </el-button>
      </div>
    </el-card>

    <template v-if="analysisDone">
      <el-row :gutter="16">
        <el-col :span="6">
          <MetricCard title="分析人数" :value="analysisResult.totalPeople" subtitle="本次分析总人数" icon="User" color="#409eff" />
        </el-col>
        <el-col :span="6">
          <MetricCard title="技能总数" :value="analysisResult.totalSkills" subtitle="覆盖技能种类" icon="Collection" color="#67c23a" />
        </el-col>
        <el-col :span="6">
          <MetricCard title="最强领域" :value="analysisResult.strongestArea" subtitle="团队核心优势" icon="Top" color="#e6a23c" />
        </el-col>
        <el-col :span="6">
          <MetricCard title="待补短板" :value="analysisResult.weakestArea" subtitle="需重点提升领域" icon="WarningFilled" color="#f56c6c" />
        </el-col>
      </el-row>

      <el-row :gutter="16" style="margin-top: 16px;">
        <el-col :span="14">
          <el-card shadow="never" class="table-card">
            <template #header>
              <div class="card-header">
                <span>团队技能覆盖矩阵</span>
                <el-tag type="info" size="small">{{ analysisResult.totalPeople }} 人 × {{ analysisResult.totalSkills }} 项技能</el-tag>
              </div>
            </template>
            <div class="table-scroll">
              <el-table :data="analysisResult.matrix" stripe border size="small" style="width: 100%">
                <el-table-column type="index" label="#" width="50" fixed />
                <el-table-column prop="name" label="姓名" width="90" fixed />
                <el-table-column v-for="skill in analysisResult.skillNames" :key="skill" :label="skill" :prop="skill" width="70" align="center">
                  <template #default="{ row }">
                    <span v-if="row[skill] === true || row[skill] === 1 || row[skill] === '√'" class="cell-check">√</span>
                    <span v-else-if="typeof row[skill] === 'number' && row[skill] > 0" class="cell-score">{{ row[skill] }}</span>
                    <span v-else class="cell-empty">—</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-card>
        </el-col>
        <el-col :span="10">
          <el-card shadow="never" class="chart-card">
            <template #header>
              <div class="card-header">
                <span>团队能力分布</span>
              </div>
            </template>
            <div ref="radarChartRef" class="chart-box"></div>
          </el-card>
        </el-col>
      </el-row>

      <div style="margin-top: 16px; text-align: center;">
        <el-button @click="resetAnalysis">重新上传</el-button>
      </div>
    </template>

    <div v-if="analyzing" class="loading-overlay">
      <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
      <p>正在批量分析 {{ fileList.length }} 份简历，请稍候...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import MetricCard from '@/components/MetricCard.vue'
import api from '../api'

const uploadRef = ref(null)
const fileList = ref([])
const analyzing = ref(false)
const analysisDone = ref(false)
const radarChartRef = ref(null)
let radarChart = null

const analysisResult = ref({
  totalPeople: 0,
  totalSkills: 0,
  strongestArea: '',
  weakestArea: '',
  skillNames: [],
  matrix: []
})

function handleFileChange(file) {
  fileList.value = [...uploadRef.value?.uploadFiles || []]
}

function handleFileRemove() {
  fileList.value = [...uploadRef.value?.uploadFiles || []]
}

async function startBatchAnalysis() {
  if (fileList.value.length === 0) return
  analyzing.value = true
  try {
    const files = fileList.value.map((f) => f.raw || f)
    const res = await api.batchUpload(files)
    const data = res?.data || res
    if (data?.matrix) {
      analysisResult.value = data
    } else if (data?.batch_id) {
      const resultRes = await api.getBatchResult(data.batch_id)
      analysisResult.value = resultRes?.data || resultRes || { totalPeople: 0, totalSkills: 0, strongestArea: '', weakestArea: '', skillNames: [], matrix: [] }
    } else {
      analysisResult.value = { totalPeople: 0, totalSkills: 0, strongestArea: '', weakestArea: '', skillNames: [], matrix: [] }
    }
  } catch (e) {
    console.error('批量分析失败:', e)
    analysisResult.value = { totalPeople: 0, totalSkills: 0, strongestArea: '', weakestArea: '', skillNames: [], matrix: [] }
  }
  analyzing.value = false
  analysisDone.value = true
  nextTick(() => initRadarChart())
}

function initRadarChart() {
  if (!radarChartRef.value) return
  radarChart?.dispose()
  radarChart = echarts.init(radarChartRef.value)

  const categories = ['编程能力', 'AI/ML', '工程实践', '数据能力', '系统设计', '软技能']
  const teamAvg = [78, 85, 62, 70, 55, 68]

  radarChart.setOption({
    tooltip: { trigger: 'item' },
    radar: {
      indicator: categories.map((c) => ({ name: c, max: 100 })),
      center: ['50%', '50%'],
      radius: '65%',
      axisName: { color: '#606266', fontSize: 12 }
    },
    series: [{
      type: 'radar',
      data: [{
        value: teamAvg,
        name: '团队均值',
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64,158,255,0.35)' },
            { offset: 1, color: 'rgba(64,158,255,0.05)' }
          ])
        },
        lineStyle: { color: '#409eff', width: 2 },
        itemStyle: { color: '#409eff' }
      }]
    }]
  })
}

function handleResize() {
  radarChart?.resize()
}

function resetAnalysis() {
  analysisDone.value = false
  fileList.value = []
  analysisResult.value = { totalPeople: 0, totalSkills: 0, strongestArea: '', weakestArea: '', skillNames: [], matrix: [] }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  radarChart?.dispose()
})
</script>

<style scoped>
.upload-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.upload-area {
  padding: 40px 0;
}

.upload-icon {
  font-size: 48px;
  color: var(--primary);
  margin-bottom: 12px;
}

.upload-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.upload-text em {
  color: var(--primary);
  font-style: normal;
  font-weight: 600;
}

.upload-tip {
  font-size: 12px;
  color: var(--text-muted);
}

.file-count-info {
  text-align: center;
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.upload-actions {
  text-align: center;
  padding-bottom: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 15px;
}

.table-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
  height: 100%;
}

.table-scroll {
  overflow-x: auto;
}

.chart-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
  height: 100%;
}

.chart-box {
  width: 100%;
  height: 360px;
}

.cell-check {
  color: #67c23a;
  font-weight: 700;
  font-size: 16px;
}

.cell-score {
  color: #409eff;
  font-weight: 600;
}

.cell-empty {
  color: var(--text-muted);
}

.loading-overlay {
  position: fixed;
  inset: 0;
  background: rgba(255,255,255,0.85);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 999;
  font-size: 16px;
  color: var(--text-secondary);
  gap: 12px;
}

.loading-icon {
  animation: rotating 1.5s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
