<template>
  <div class="page-container">
    <div class="page-header">
      <h2>What-If 分析</h2>
      <p>模拟学习新技能对岗位匹配度的影响，辅助制定学习优先级</p>
    </div>

    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span>当前技能概览</span>
          <el-tag type="info" size="small">{{ currentSkills.length }} 项技能</el-tag>
        </div>
      </template>
      <div class="skills-tags">
        <el-tag
          v-for="s in currentSkills"
          :key="s"
          type="primary"
          size="small"
          class="skill-tag"
          closable
          @close="removeSkill(s)"
        >
          {{ s }}
        </el-tag>
        <el-popover placement="bottom" trigger="click" width="260">
          <template #reference>
            <el-button size="small" circle>
              <el-icon><Plus /></el-icon>
            </el-button>
          </template>
          <div class="popover-skills">
            <el-tag
              v-for="s in availableBaseSkills"
              :key="s"
              :type="currentSkills.includes(s) ? 'info' : ''"
              size="small"
              class="skill-tag"
              :disabled="currentSkills.includes(s)"
              style="cursor: pointer;"
              @click="addBaseSkill(s)"
            >
              {{ s }}
            </el-tag>
          </div>
        </el-popover>
      </div>
    </el-card>

    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span>新增技能选择</span>
          <el-tag type="warning" size="small">模拟目标</el-tag>
        </div>
      </template>
      <el-row :gutter="16" align="middle">
        <el-col :span="18">
          <el-select
            v-model="selectedNewSkills"
            multiple
            placeholder="请选择要模拟新增的技能"
            style="width: 100%"
            filterable
            clearable
          >
            <el-option
              v-for="s in allCandidateSkills"
              :key="s"
              :label="s"
              :value="s"
              :disabled="currentSkills.includes(s)"
            />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-button
            type="primary"
            size="large"
            style="width: 100%"
            :loading="simulating"
            :disabled="selectedNewSkills.length === 0"
            @click="startSimulation"
          >
            开始模拟
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <template v-if="simResult">
      <el-card shadow="never" class="section-card">
        <template #header>
          <div class="card-header">
            <span>结果对比</span>
            <el-tag type="success" size="small">模拟完成</el-tag>
          </div>
        </template>
        <div ref="compareChartRef" class="chart-box"></div>
      </el-card>

      <el-card shadow="never" class="section-card">
        <template #header>
          <div class="card-header">
            <span>改进建议</span>
          </div>
        </template>
        <div class="suggestion-list">
          <div v-for="(item, idx) in simResult.suggestions" :key="idx" class="suggestion-item">
            <span class="suggestion-index">{{ idx + 1 }}</span>
            <span class="suggestion-text">{{ item }}</span>
          </div>
        </div>
      </el-card>
    </template>

    <div v-if="!simulating && !simResult" class="empty-state">
      <el-icon><SetUp /></el-icon>
      <p>选择要模拟新增的技能后点击「开始模拟」查看匹配度变化</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import api from '../api'
import { useResumeStore } from '../stores/resume'

const resumeStore = useResumeStore()

// 优先从 store 读真实技能，没有时为空
const currentSkills = ref([])

const availableBaseSkills = [
  'JavaScript', 'TypeScript', 'Vue.js', 'React', 'Go', 'Rust', 'Java', 'Spring Boot',
  'MySQL', 'MongoDB', 'Redis', 'Nginx'
]

const allCandidateSkills = [
  'LangChain', 'RAG', 'Docker', 'Kubernetes', 'PyTorch', 'TensorFlow',
  'AWS', 'Redis', 'Kafka', 'Flink', 'Vue.js', 'React', 'Go', 'Rust',
  'Spark', 'Airflow', 'Kubernetes', 'CI/CD', '微服务', 'TypeScript'
]

const selectedNewSkills = ref([])
const simulating = ref(false)
const simResult = ref(null)

const compareChartRef = ref(null)
let compareChart = null

function removeSkill(s) {
  currentSkills.value = currentSkills.value.filter(x => x !== s)
}

function addBaseSkill(s) {
  if (!currentSkills.value.includes(s)) {
    currentSkills.value.push(s)
  }
}

function initCompareChart() {
  if (!simResult.value || !compareChartRef.value) return

  compareChart?.dispose()
  compareChart = echarts.init(compareChartRef.value)

  const jobs = simResult.value.before.map(item => item.job)
  const beforeData = simResult.value.before.map(item => item.score)
  const afterData = simResult.value.after.map(item => item.score)

  compareChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: jobs,
      axisLabel: { fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      name: '匹配分数',
      min: 0,
      max: 100
    },
    legend: {
      data: ['模拟前', '模拟后'],
      bottom: 0,
      left: 'center'
    },
    series: [
      {
        name: '模拟前',
        type: 'bar',
        data: beforeData,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#909399' },
            { offset: 1, color: '#c0c4cc' }
          ])
        },
        barWidth: '30%'
      },
      {
        name: '模拟后',
        type: 'bar',
        data: afterData,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#67c23a' },
            { offset: 1, color: '#95d475' }
          ])
        },
        barWidth: '30%'
      }
    ]
  })
}

async function startSimulation() {
  if (selectedNewSkills.value.length === 0) {
    ElMessage.warning('请选择要模拟新增的技能')
    return
  }
  if (currentSkills.value.length === 0) {
    ElMessage.warning('当前技能为空，请先在简历分析页上传简历')
    return
  }

  simulating.value = true
  simResult.value = null

  try {
    // 后端 whatif 接口需要 resume_id 和 added_skills
    const params = {
      resume_id: resumeStore.resumeId || undefined,
      added_skills: selectedNewSkills.value
    }
    const res = await api.whatIf(params)
    const data = res?.data || res || {}
    // 构造图表数据
    const original = data.original_top3 || []
    const enhanced = data.enhanced_top3 || []
    simResult.value = {
      before: original.map(m => ({ job: m.job_title, score: Math.round((m.match_score || 0) * 100) })),
      after: enhanced.map(m => ({ job: m.job_title, score: Math.round((m.match_score || 0) * 100) })),
      comparison: data.comparison,
      recommendation: data.recommendation,
    }
  } catch (e) {
    console.error('What-If 模拟失败:', e)
    ElMessage.error('What-If 模拟失败：' + (e.message || ''))
    simResult.value = null
  }

  simulating.value = false
  await nextTick()
  initCompareChart()
}

function handleResize() {
  compareChart?.resize()
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  // 从 store 读真实技能
  if (resumeStore.skills.length > 0) {
    currentSkills.value = [...resumeStore.skills]
    ElMessage.success(`已从简历分析带入 ${currentSkills.value.length} 项技能`)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  compareChart?.dispose()
})
</script>

<style scoped>
.section-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 15px;
}

.skills-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.skill-tag {
  margin: 0 2px;
}

.popover-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 4px 0;
}

.chart-box {
  width: 100%;
  height: 360px;
}

.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.suggestion-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  background: var(--bg-color);
  border-radius: 6px;
  border: 1px solid var(--border-color);
}

.suggestion-index {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.suggestion-text {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.6;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: var(--text-muted);
}

.empty-state .el-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state p {
  font-size: 14px;
}
</style>
