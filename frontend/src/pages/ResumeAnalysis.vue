<template>
  <div class="page-container">
    <div class="page-header">
      <h2>简历分析</h2>
      <p>上传简历进行深度解析、技能评估与可信度分析</p>
    </div>

    <el-card v-if="!resumeData" shadow="never" class="upload-card">
      <div class="upload-area">
        <el-upload
          drag
          accept=".pdf,.docx,.doc,.txt"
          :before-upload="handleUpload"
          :show-file-list="false"
          :loading="uploading"
        >
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="upload-text">
            <span>拖拽简历文件到此处，或 <em>点击上传</em></span>
          </div>
          <template #tip>
            <div class="upload-tip">
              支持 PDF、DOCX、TXT 格式，文件大小不超过 10MB
            </div>
          </template>
        </el-upload>
      </div>
    </el-card>

    <template v-if="resumeData">
      <el-row :gutter="16">
        <el-col :span="6">
          <MetricCard
            title="候选人"
            :value="resumeData.name"
            :subtitle="`技能数: ${resumeData.skills?.length || 0}`"
            icon="User"
            color="#409eff"
          />
        </el-col>
        <el-col :span="6">
          <MetricCard
            title="可信度分数"
            :value="resumeData.credibilityScore ?? '--'"
            subtitle="综合可信度评估"
            icon="CircleCheck"
            :color="credibilityColor"
          />
        </el-col>
        <el-col :span="6">
          <MetricCard
            title="技能匹配度"
            :value="resumeData.matchRate ?? '--'"
            subtitle="与目标岗位匹配率"
            icon="TrendCharts"
            color="#67c23a"
          />
        </el-col>
        <el-col :span="6">
          <MetricCard
            title="项目经验"
            :value="resumeData.projects?.length || 0"
            subtitle="参与项目数量"
            icon="FolderOpened"
            color="#e6a23c"
          />
        </el-col>
      </el-row>

      <el-card shadow="never" class="detail-card" style="margin-top: 16px;">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="基本信息" name="basic">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="姓名">{{ resumeData.name || '--' }}</el-descriptions-item>
              <el-descriptions-item label="邮箱">{{ resumeData.email || '--' }}</el-descriptions-item>
              <el-descriptions-item label="电话">{{ resumeData.phone || '--' }}</el-descriptions-item>
              <el-descriptions-item label="求职意向">{{ resumeData.intent || '--' }}</el-descriptions-item>
              <el-descriptions-item label="技能总数">{{ resumeData.skills?.length || 0 }}</el-descriptions-item>
              <el-descriptions-item label="可信度分数">
                <el-tag :type="credibilityTagType" size="small">{{ resumeData.credibilityScore ?? '--' }}</el-tag>
              </el-descriptions-item>
            </el-descriptions>
            <el-divider />
            <h4 style="margin-bottom: 12px;">技能标签</h4>
            <div class="skills-tags">
              <el-tag
                v-for="skill in resumeData.skills"
                :key="skill"
                type="primary"
                size="small"
                style="margin: 0 6px 6px 0"
              >
                {{ skill }}
              </el-tag>
              <span v-if="!resumeData.skills?.length" class="text-muted">暂无技能数据</span>
            </div>
          </el-tab-pane>

          <el-tab-pane label="技能分析" name="skills">
            <div ref="radarChartRef" class="chart-box"></div>
          </el-tab-pane>

          <el-tab-pane label="项目经验" name="projects">
            <el-table :data="resumeData.projects || []" stripe style="width: 100%">
              <el-table-column type="index" label="#" width="50" />
              <el-table-column prop="name" label="项目名称" min-width="160" />
              <el-table-column prop="role" label="角色" width="140" />
              <el-table-column prop="techStack" label="技术栈" min-width="200">
                <template #default="{ row }">
                  <el-tag
                    v-for="t in row.techStack"
                    :key="t"
                    size="small"
                    style="margin: 0 4px 4px 0"
                  >
                    {{ t }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="description" label="描述" min-width="240" show-overflow-tooltip />
            </el-table>
            <div v-if="!resumeData.projects?.length" class="empty-state">
              <p>暂无项目经验数据</p>
            </div>
          </el-tab-pane>

          <el-tab-pane label="可信度评估" name="credibility">
            <el-row :gutter="16">
              <el-col :span="12">
                <div ref="credibilityChartRef" class="chart-box"></div>
              </el-col>
              <el-col :span="12">
                <div v-if="resumeData?.credibilityScore !== null && resumeData?.credibilityScore !== undefined" class="credibility-info">
                  <p style="font-size: 14px; color: #606266;">综合可信度分数</p>
                  <p style="font-size: 32px; font-weight: 700;" :style="{ color: credibilityColor }">
                    {{ Math.round(resumeData.credibilityScore * 100) }}分
                  </p>
                  <el-tag :type="credibilityTagType" size="default">
                    {{ resumeData.credibilityScore >= 0.85 ? '高可信度' : resumeData.credibilityScore >= 0.6 ? '中等可信度' : '低可信度' }}
                  </el-tag>
                  <p style="font-size: 13px; color: #909399; margin-top: 12px;">
                    可信度分数基于技能与项目的交叉验证，分数越高代表简历中声明的能力越有项目经验支撑。
                  </p>
                </div>
                <div v-else class="empty-state">
                  <p>暂无可信度评估数据</p>
                </div>
              </el-col>
            </el-row>
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <div style="margin-top: 16px; text-align: center;">
        <el-button @click="resetAnalysis">重新上传</el-button>
        <el-button type="primary" @click="goToMatching" :disabled="!resumeStore.resumeId">
          基于此简历匹配岗位
        </el-button>
      </div>
    </template>

    <div v-if="uploading" class="loading-overlay">
      <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
      <p>正在解析简历，请稍候...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import MetricCard from '@/components/MetricCard.vue'
import api from '../api'
import { useResumeStore } from '../stores/resume'

const router = useRouter()
const resumeStore = useResumeStore()

const activeTab = ref('basic')
const uploading = ref(false)
const uploadCardRef = ref(null)

const radarChartRef = ref(null)
const credibilityChartRef = ref(null)

let radarChart = null
let credibilityChart = null

const resumeData = ref(null)

const credibilityDetails = ref([])

const credibilityColor = computed(() => {
  const score = resumeData.value?.credibilityScore
  if (!score && score !== 0) return '#909399'
  if (score >= 0.85) return '#67c23a'
  if (score >= 0.6) return '#e6a23c'
  return '#f56c6c'
})

const credibilityTagType = computed(() => {
  const score = resumeData.value?.credibilityScore
  if (!score && score !== 0) return 'info'
  if (score >= 0.85) return 'success'
  if (score >= 0.6) return 'warning'
  return 'danger'
})

function scoreType(score) {
  if (score >= 85) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

async function handleUpload(file) {
  uploading.value = true
  try {
    const uploadRes = await api.uploadResume(file)
    // 后端响应被 axios 拦截器剥了一层，resume_id 在 data 里
    const resumeId = uploadRes?.data?.resume_id
    if (resumeId) {
      const profileRes = await api.getResumeProfile(resumeId)
      const profile = profileRes?.data || {}
      // 把后端字段映射成前端模板期望的结构
      const allSkills = [
        ...(profile.skills_explicit || []),
        ...(profile.skills_implicit || [])
      ]
      resumeData.value = {
        name: profile.name || '匿名候选人',
        email: profile.email || '',
        phone: profile.phone || '',
        intent: '',
        credibilityScore: profile.credibility_score ?? uploadRes?.data?.credibility_score,
        matchRate: '--',
        skills: allSkills,
        projects: (profile.projects || []).map(p => ({
          name: p.project_name || p.name || '',
          role: p.role || '',
          techStack: p.technologies_used || [],
          description: p.description || ''
        }))
      }
      // 存入全局 store，供匹配/差距分析/WhatIf 页面使用
      resumeStore.setResume(resumeId, profile.name, allSkills, profile.credibility_score)
      ElMessage.success(`简历解析成功，已识别 ${allSkills.length} 项技能`)
    } else {
      ElMessage.error('上传成功但未获取到 resume_id')
    }
  } catch (e) {
    console.error('[简历上传失败]', e)
    ElMessage.error('简历上传失败：' + (e.message || '请检查后端服务'))
  }
  uploading.value = false
  return false
}

function goToMatching() {
  if (resumeStore.resumeId) {
    router.push({ name: 'JobMatching' })
  }
}

function initRadarChart() {
  if (!radarChartRef.value || !resumeData.value) return

  radarChart = echarts.init(radarChartRef.value)
  radarChart.setOption({
    tooltip: {},
    radar: {
      indicator: [
        { name: '编程能力', max: 100 },
        { name: '框架掌握', max: 100 },
        { name: 'AI/ML', max: 100 },
        { name: '工程实践', max: 100 },
        { name: '系统设计', max: 100 },
        { name: '软技能', max: 100 }
      ],
      center: ['50%', '50%'],
      radius: '65%',
      shape: 'circle',
      axisName: { color: '#606266', fontSize: 12 }
    },
    series: [{
      type: 'radar',
      data: [{ value: [85, 78, 88, 72, 68, 75] }],
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64,158,255,0.4)' },
          { offset: 1, color: 'rgba(64,158,255,0.05)' }
        ])
      },
      lineStyle: { color: '#409eff', width: 2 },
      itemStyle: { color: '#409eff' }
    }]
  })
}

function initCredibilityChart() {
  if (!credibilityChartRef.value) return

  credibilityChart = echarts.init(credibilityChartRef.value)
  credibilityChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: credibilityDetails.value.map((d) => d.dimension),
      axisLabel: { fontSize: 10, interval: 0, rotate: 20 }
    },
    yAxis: { type: 'value', name: '分数', min: 0, max: 100 },
    series: [{
      type: 'bar',
      data: credibilityDetails.value.map((d) => ({
        value: d.score,
        itemStyle: {
          color: d.score >= 85 ? '#67c23a' : d.score >= 60 ? '#e6a23c' : '#f56c6c',
          borderRadius: [4, 4, 0, 0]
        }
      })),
      barWidth: '45%',
      label: {
        show: true,
        position: 'top',
        formatter: '{c}分',
        fontSize: 10
      }
    }]
  })
}

function handleResize() {
  radarChart?.resize()
  credibilityChart?.resize()
}

function resetAnalysis() {
  resumeData.value = null
  activeTab.value = 'basic'
}

watch(activeTab, (tab) => {
  nextTick(() => {
    if (tab === 'skills') initRadarChart()
    if (tab === 'credibility') initCredibilityChart()
  })
})

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  radarChart?.dispose()
  credibilityChart?.dispose()
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

.chart-box {
  width: 100%;
  height: 360px;
}

.detail-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.skills-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.text-muted {
  color: var(--text-muted);
  font-size: 13px;
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
