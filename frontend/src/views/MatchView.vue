<template>
  <div class="match-view">
    <!-- 模式切换 -->
    <el-card class="control-bar">
      <el-radio-group v-model="store.currentMode" size="large" @change="onModeChange">
        <el-radio-button label="jd">
          <el-icon><Document /></el-icon>
          <span>具体 JD 匹配</span>
        </el-radio-button>
        <el-radio-button label="role">
          <el-icon><Trophy /></el-icon>
          <span>岗位方向 Top-N</span>
        </el-radio-button>
      </el-radio-group>
      <el-tag class="ml-16" :type="store.currentMode === 'jd' ? 'primary' : 'warning'">
        {{ store.currentMode === 'jd' ? '精准匹配' : '方向探索' }}
      </el-tag>
    </el-card>

    <el-row :gutter="16" class="main-row">
      <!-- 左侧：输入区 -->
      <el-col :span="8">
        <el-card class="input-card">
          <template #header><span>输入</span></template>

          <!-- 简历上传 -->
          <el-form label-position="top" size="default">
            <el-form-item label="1. 上传或选择简历">
              <ResumeUploader
                v-if="!resumeId"
                @uploaded="onResumeUploaded"
              />
              <div v-else class="resume-info">
                <el-alert :title="`已选简历：${resumeId}`" type="success" :closable="false">
                  <div class="text-muted" style="font-size:12px">可继续上传新简历替换</div>
                </el-alert>
                <el-button size="small" type="danger" plain @click="resumeId = ''" class="mt-16">
                  移除
                </el-button>
              </div>
            </el-form-item>

            <!-- JD 选择（仅具体 JD 模式） -->
            <el-form-item v-if="store.currentMode === 'jd'" label="2. 选择 JD">
              <JDSelector v-model="jdId" />
            </el-form-item>

            <!-- Top-N（仅方向模式） -->
            <el-form-item v-else label="2. Top-N 数量">
              <el-input-number v-model="topN" :min="1" :max="50" />
            </el-form-item>

            <el-button
              type="primary"
              :loading="store.loading"
              :disabled="!resumeId || (store.currentMode === 'jd' && !jdId)"
              class="full-btn"
              @click="startMatch"
            >
              <el-icon><Promotion /></el-icon>
              <span>开始匹配</span>
            </el-button>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：结果区 -->
      <el-col :span="16">
        <!-- 具体 JD 模式结果 -->
        <template v-if="store.currentMode === 'jd' && store.currentResult">
          <MatchScore :result="store.currentResult" class="mb-16" />
          <MatchBreakdown :result="store.currentResult" class="mb-16" />
          <GapAnalysis :gaps="store.currentResult.gap_skills" class="mb-16" />
          <LearningPath :path="store.currentResult.learning_path" :recommendations="store.currentResult.recommendations" />
        </template>

        <!-- 方向匹配 Top-N 结果 -->
        <template v-else-if="store.currentMode === 'role'">
          <RoleRanking :results="store.topNResults" :loading="store.loading" />
        </template>

        <el-empty v-else description="请上传简历并开始匹配" />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useMatchStore } from '@/stores/match'
import ResumeUploader from '@/components/ResumeUploader.vue'
import JDSelector from '@/components/JDSelector.vue'
import MatchScore from '@/components/MatchScore.vue'
import MatchBreakdown from '@/components/MatchBreakdown.vue'
import GapAnalysis from '@/components/GapAnalysis.vue'
import LearningPath from '@/components/LearningPath.vue'
import RoleRanking from '@/components/RoleRanking.vue'

const store = useMatchStore()
const resumeId = ref('')
const jdId = ref('')
const topN = ref(10)

const onModeChange = () => {
  store.currentResult = null
  store.topNResults = []
}

const onResumeUploaded = (id) => {
  resumeId.value = id
  ElMessage.success(`简历上传成功：${id}`)
}

const startMatch = async () => {
  if (!resumeId.value) {
    ElMessage.warning('请先上传简历')
    return
  }
  try {
    if (store.currentMode === 'jd') {
      if (!jdId.value) {
        ElMessage.warning('请选择 JD')
        return
      }
      await store.doMatchJd({ resume_id: resumeId.value, jd_id: jdId.value })
    } else {
      await store.doMatchRole({ resume_id: resumeId.value, top_n: topN.value })
    }
  } catch (e) {
    // request 拦截器已提示
  }
}
</script>

<style lang="scss" scoped>
.match-view {
  max-width: 1400px;
  margin: 0 auto;
}

.control-bar {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.main-row {
  min-height: 600px;
}

.input-card {
  height: 100%;
  min-height: 400px;
}

.full-btn {
  width: 100%;
  margin-top: 8px;
}

.resume-info {
  .mt-16 { margin-top: 12px; }
}

.ml-16 { margin-left: 16px; }

.mb-16 { margin-bottom: 16px; }
</style>
