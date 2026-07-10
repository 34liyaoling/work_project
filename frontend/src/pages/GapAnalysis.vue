<template>
  <div class="page-container">
    <div class="page-header">
      <h2>差距分析</h2>
      <p>基于知识图谱对比目标岗位技能要求，精准识别技能差距与学习路径</p>
    </div>

    <el-card shadow="never" class="param-card">
      <el-row :gutter="16" align="middle">
        <el-col :span="8">
          <div class="param-item">
            <label class="param-label">目标岗位</label>
            <el-select v-model="targetJob" placeholder="请选择目标岗位" style="width: 100%" clearable filterable>
              <el-option
                v-for="j in jobList"
                :key="j.id || j.title"
                :label="j.title || j"
                :value="j.id || j.title || j"
              />
            </el-select>
          </div>
        </el-col>
        <el-col :span="2">
          <el-button type="primary" size="large" style="width: 100%; margin-top: 22px;" :loading="analyzing" @click="startAnalysis">
            开始分析
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <template v-if="analysisResult">
      <div class="result-header">
        <div class="match-rate-section">
          <el-progress type="circle" :percentage="analysisResult.matchRate" :stroke-width="10" :size="140" :color="matchRateColor">
            <span class="match-rate-text">{{ analysisResult.matchRate }}%</span>
          </el-progress>
          <div class="match-rate-info">
            <h3>综合匹配率</h3>
            <p>与「{{ targetJob }}」岗位要求对比</p>
          </div>
        </div>
      </div>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-card shadow="never" class="skill-card">
            <template #header>
              <div class="card-header">
                <span>已有技能</span>
                <el-tag type="success" size="small">{{ analysisResult.existingSkills.length }} 项</el-tag>
              </div>
            </template>
            <div class="skills-list">
              <el-tag
                v-for="s in analysisResult.existingSkills"
                :key="s"
                type="success"
                size="small"
                class="skill-tag"
              >
                {{ s }}
              </el-tag>
              <div v-if="analysisResult.existingSkills.length === 0" class="text-muted">暂无匹配技能</div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never" class="skill-card">
            <template #header>
              <div class="card-header">
                <span>缺失技能</span>
                <el-tag type="danger" size="small">{{ analysisResult.missingCritical.length }} 项关键</el-tag>
              </div>
            </template>
            <div class="skills-list">
              <div class="missing-section" v-if="analysisResult.missingCritical.length > 0">
                <div class="missing-label">关键技能</div>
                <el-tag
                  v-for="s in analysisResult.missingCritical"
                  :key="s"
                  type="danger"
                  size="small"
                  class="skill-tag"
                >
                  {{ s }}
                </el-tag>
              </div>
              <div class="missing-section" v-if="analysisResult.missingOptional.length > 0">
                <div class="missing-label optional">可选技能</div>
                <el-tag
                  v-for="s in analysisResult.missingOptional"
                  :key="s"
                  type="warning"
                  size="small"
                  class="skill-tag"
                >
                  {{ s }}
                </el-tag>
              </div>
              <div v-if="analysisResult.missingCritical.length === 0 && analysisResult.missingOptional.length === 0" class="text-muted">
                无缺失技能
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="never" class="table-card">
        <template #header>
          <div class="card-header">
            <span>学习路径规划</span>
            <el-tag type="info" size="small">{{ analysisResult.learningPath.length }} 个步骤</el-tag>
          </div>
        </template>
        <el-table :data="analysisResult.learningPath" stripe style="width: 100%" size="small">
          <el-table-column type="index" label="步骤" width="60" />
          <el-table-column prop="skillName" label="技能名称" min-width="130" />
          <el-table-column prop="difficulty" label="难度" width="90">
            <template #default="{ row }">
              <el-tag :type="difficultyType(row.difficulty)" size="small">{{ row.difficulty }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="duration" label="建议时长" width="100" />
          <el-table-column prop="resources" label="推荐资源" min-width="200">
            <template #default="{ row }">
              <span v-if="Array.isArray(row.resources)">{{ row.resources.join('、') }}</span>
              <span v-else>{{ row.resources }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="roiScore" label="ROI评分" width="90" sortable>
            <template #default="{ row }">
              <el-progress :percentage="row.roiScore" :stroke-width="12" :color="roiColor(row.roiScore)" :format="() => row.roiScore + '分'" />
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <div v-if="!analyzing && !analysisResult" class="empty-state">
      <el-icon><TrendCharts /></el-icon>
      <p>选择目标岗位后点击「开始分析」查看差距分析结果</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import { useResumeStore } from '../stores/resume'

const route = useRoute()
const resumeStore = useResumeStore()

const targetJob = ref('')
const jobList = ref([])
const analyzing = ref(false)
const analysisResult = ref(null)

function matchRateColor(percentage) {
  if (percentage >= 80) return '#67c23a'
  if (percentage >= 60) return '#e6a23c'
  return '#f56c6c'
}

function difficultyType(d) {
  if (d === '入门' || d === '简单') return 'success'
  if (d === '中等') return 'warning'
  return 'danger'
}

function roiColor(score) {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#409eff'
  if (score >= 40) return '#e6a23c'
  return '#f56c6c'
}

async function startAnalysis() {
  if (!targetJob.value) {
    ElMessage.warning('请选择目标岗位')
    return
  }
  if (!resumeStore.resumeId) {
    ElMessage.warning('请先在简历分析页面上传简历')
    return
  }
  analyzing.value = true
  try {
    const res = await api.gapAnalysis({
      resume_id: resumeStore.resumeId,
      target_job: targetJob.value
    })
    const data = res?.data || res || {}
    analysisResult.value = data
  } catch (e) {
    console.error('差距分析失败:', e)
    ElMessage.error('差距分析失败：' + (e.message || ''))
    analysisResult.value = null
  }
  analyzing.value = false
}

onMounted(async () => {
  // 从 URL query 带入目标岗位（从匹配页跳转过来）
  if (route.query.target_job) {
    targetJob.value = route.query.target_job
  }
  // 如果 store 有 resume_id，提示已带入
  if (resumeStore.resumeId) {
    ElMessage.info(`已自动带入简历：${resumeStore.candidateName || '匿名'}`)
  }
  try {
    const jobs = await api.getJobs()
    if (Array.isArray(jobs)) {
      jobList.value = jobs
    } else if (jobs?.jobs) {
      jobList.value = jobs.jobs
    } else if (jobs?.data) {
      jobList.value = jobs.data
    }
  } catch {
    jobList.value = []
  }
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

.result-header {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}

.match-rate-section {
  display: flex;
  align-items: center;
  gap: 24px;
  background: #fff;
  border-radius: 8px;
  padding: 28px 40px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.match-rate-text {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.match-rate-info h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.match-rate-info p {
  font-size: 13px;
  color: var(--text-secondary);
}

.skill-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
  margin-bottom: 16px;
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 15px;
}

.skills-list {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 6px;
}

.skill-tag {
  margin: 0 4px 4px 0;
}

.missing-section {
  width: 100%;
  margin-bottom: 12px;
}

.missing-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 6px;
  font-weight: 500;
}

.missing-label.optional {
  margin-top: 8px;
}

.text-muted {
  color: var(--text-muted);
  font-size: 13px;
}

.table-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
  margin-top: 8px;
}
</style>
