<template>
  <div class="page-container">
    <div class="page-header">
      <h2>新岗位发现</h2>
      <p>AI驱动的岗位发现引擎 — 从多源数据中识别新兴岗位需求</p>
    </div>

    <el-card shadow="never" class="discovery-card">
      <div class="discovery-header">
        <div class="discovery-info">
          <span class="discovery-label">数据源覆盖：</span>
          <el-tag size="small" type="info">LinkedIn</el-tag>
          <el-tag size="small" type="info">拉勾</el-tag>
          <el-tag size="small" type="info">51Job</el-tag>
          <el-tag size="small" type="info">Boss直聘</el-tag>
          <el-tag size="small" type="info">行业报告</el-tag>
        </div>
        <el-button type="primary" size="large" :loading="discovering" @click="startDiscovery">
          开始发现
        </el-button>
      </div>
    </el-card>

    <template v-if="discoveredJobs.length > 0">
      <div class="result-summary">
        共发现 <strong>{{ discoveredJobs.length }}</strong> 个候选新兴岗位
      </div>

      <div class="job-list">
        <el-card
          v-for="job in discoveredJobs"
          :key="job.id"
          shadow="never"
          class="job-card"
          :class="{ 'job-expanded': job.expanded }"
        >
          <div class="job-card-header" @click="toggleExpand(job)">
            <div class="job-title-row">
              <h3 class="job-title">{{ job.title }}</h3>
              <el-tag
                :type="confidenceType(job.confidence)"
                size="small"
                class="confidence-tag"
              >
                {{ job.confidence }}% 置信度
              </el-tag>
            </div>
            <div class="job-meta">
              <span class="meta-item">
                <el-icon><TrendCharts /></el-icon>
                增长率 {{ job.growthRate }}
              </span>
              <span class="meta-item">
                <el-icon><DataBoard /></el-icon>
                {{ job.source }}
              </span>
              <span class="meta-item">
                <el-icon><Clock /></el-icon>
                {{ job.discoveredAt }}
              </span>
            </div>
            <div class="skill-clusters">
              <el-tag
                v-for="skill in job.skillTags"
                :key="skill"
                size="small"
                type="primary"
                class="skill-tag"
              >
                {{ skill }}
              </el-tag>
            </div>
            <el-icon class="expand-icon" :class="{ 'expand-rotated': job.expanded }">
              <ArrowDown />
            </el-icon>
          </div>

          <transition name="expand">
            <div v-if="job.expanded" class="job-detail">
              <el-divider />
              <div class="detail-section">
                <h4>岗位定义</h4>
                <p class="detail-text">{{ job.description }}</p>
              </div>
              <div class="detail-section">
                <h4>核心职责</h4>
                <ul class="responsibility-list">
                  <li v-for="(resp, idx) in job.responsibilities" :key="idx">{{ resp }}</li>
                </ul>
              </div>
              <div class="detail-section">
                <h4>所需技能</h4>
                <div class="required-skills">
                  <div v-for="skill in job.requiredSkills" :key="skill.name" class="skill-item">
                    <span class="skill-name">{{ skill.name }}</span>
                    <el-tag
                      size="small"
                      :type="proficiencyType(skill.proficiency)"
                    >
                      {{ skill.proficiency }}
                    </el-tag>
                  </div>
                </div>
              </div>
            </div>
          </transition>

          <el-divider v-if="!job.expanded" />
          <div class="job-actions">
            <el-button type="success" size="small" :loading="job.approving" @click.stop="approveJob(job)">
              批准
            </el-button>
            <el-button type="danger" size="small" :loading="job.rejecting" @click.stop="rejectJob(job)">
              拒绝
            </el-button>
          </div>
        </el-card>
      </div>
    </template>

    <div v-if="!discovering && discoveredJobs.length === 0" class="empty-state">
      <el-icon size="48" color="var(--text-muted)"><Search /></el-icon>
      <p>点击「开始发现」按钮，AI将自动分析多源数据并识别新兴岗位</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../api'

const discovering = ref(false)
const discoveredJobs = ref([])

function confidenceType(score) {
  if (score >= 85) return 'success'
  if (score >= 70) return 'primary'
  if (score >= 50) return 'warning'
  return 'info'
}

function proficiencyType(level) {
  if (level === '精通' || level === '高级') return 'danger'
  if (level === '熟练' || level === '中级') return 'warning'
  return 'primary'
}

async function startDiscovery() {
  discovering.value = true
  try {
    const res = await api.discoverJobs()
    const candidates = res?.candidates || res?.data?.candidates || (Array.isArray(res) ? res : [])
    if (candidates.length > 0) {
      discoveredJobs.value = candidates.map((j) => ({
        ...j,
        expanded: false,
        approving: false,
        rejecting: false
      }))
    } else if (Array.isArray(res) && res.length > 0) {
      discoveredJobs.value = res.map((j) => ({
        ...j,
        expanded: false,
        approving: false,
        rejecting: false
      }))
    }
  } catch (error) {
    console.error('岗位发现请求失败:', error.message)
  }
  discovering.value = false
}

function toggleExpand(job) {
  job.expanded = !job.expanded
}

async function approveJob(job) {
  job.approving = true
  try {
    await api.approveJob({ id: job.id, action: 'approve', title: job.title })
    discoveredJobs.value = discoveredJobs.value.filter((j) => j.id !== job.id)
  } catch {
    discoveredJobs.value = discoveredJobs.value.filter((j) => j.id !== job.id)
  }
}

async function rejectJob(job) {
  job.rejecting = true
  try {
    await api.approveJob({ id: job.id, action: 'reject', title: job.title })
    discoveredJobs.value = discoveredJobs.value.filter((j) => j.id !== job.id)
  } catch {
    discoveredJobs.value = discoveredJobs.value.filter((j) => j.id !== job.id)
  }
}
</script>

<style scoped>
.discovery-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
  margin-bottom: 24px;
}

.discovery-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.discovery-info {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.discovery-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.result-summary {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.job-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.job-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.job-card:hover {
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.job-card-header {
  position: relative;
  padding-right: 28px;
}

.job-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.job-title {
  font-size: 17px;
  font-weight: 600;
  margin: 0;
  color: var(--text-primary);
}

.confidence-tag {
  flex-shrink: 0;
}

.job-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 10px;
  font-size: 12px;
  color: var(--text-secondary);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.meta-item .el-icon {
  font-size: 14px;
}

.skill-clusters {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-tag {
  margin: 0;
}

.expand-icon {
  position: absolute;
  right: 0;
  top: 4px;
  font-size: 18px;
  color: var(--text-muted);
  transition: transform 0.25s;
}

.expand-rotated {
  transform: rotate(180deg);
}

.job-detail {
  padding-top: 4px;
}

.detail-section {
  margin-bottom: 20px;
}

.detail-section h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.detail-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
  margin: 0;
}

.responsibility-list {
  margin: 0;
  padding-left: 20px;
}

.responsibility-list li {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.8;
}

.required-skills {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skill-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  background: #f5f7fa;
  border-radius: 6px;
}

.skill-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.job-actions {
  display: flex;
  gap: 8px;
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.empty-state {
  padding: 80px 0;
  text-align: center;
  color: var(--text-muted);
  font-size: 14px;
}

.empty-state p {
  margin-top: 16px;
}
</style>
