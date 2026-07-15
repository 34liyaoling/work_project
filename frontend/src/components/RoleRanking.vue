<template>
  <el-card class="role-ranking" v-loading="loading">
    <template #header>
      <div class="card-header">
        <span>岗位方向 Top-N 排名</span>
        <el-tag size="small">{{ results.length }} 个结果</el-tag>
      </div>
    </template>
    <el-empty v-if="!loading && results.length === 0" description="暂无匹配结果" />
    <el-table v-else :data="results" stripe size="default">
      <el-table-column type="index" label="#" width="60" />
      <el-table-column prop="role" label="岗位" min-width="180">
        <template #default="{ row }">
          <div class="role-name">
            <el-icon><Trophy /></el-icon>
            <span>{{ row.role }}</span>
          </div>
          <div v-if="row.category" class="role-meta">
            <el-tag size="small" effect="plain">{{ row.category }}</el-tag>
            <el-tag v-if="row.level" size="small" type="info" effect="plain">{{ row.level }}</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="总体匹配率" width="160">
        <template #default="{ row }">
          <div class="score-cell">
            <span class="score-val" :style="{ color: scoreColor(row.overall_score) }">
              {{ formatPercent(row.overall_score) }}
            </span>
            <el-progress
              :percentage="Math.round((row.overall_score || 0) * 100)"
              :stroke-width="6"
              :show-text="false"
            />
          </div>
        </template>
      </el-table-column>
      <el-table-column label="必备技能" width="120">
        <template #default="{ row }">
          {{ formatPercent(row.required_score) }}
        </template>
      </el-table-column>
      <el-table-column label="已具备技能" min-width="200">
        <template #default="{ row }">
          <el-tag
            v-for="s in (row.matched_skills || []).slice(0, 5)"
            :key="s"
            type="success"
            size="small"
            effect="light"
            style="margin: 2px"
          >{{ s }}</el-tag>
          <el-tag
            v-if="(row.matched_skills || []).length > 5"
            size="small"
            type="info"
            effect="plain"
          >+{{ row.matched_skills.length - 5 }}</el-tag>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { formatPercent, scoreColor } from '@/utils/format'

defineProps({
  results: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})
</script>

<style lang="scss" scoped>
.role-ranking {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
  }
  .role-name {
    display: flex;
    align-items: center;
    gap: 4px;
    font-weight: 600;
    .el-icon { color: #f59e0b; }
  }
  .role-meta {
    display: flex;
    gap: 4px;
    margin-top: 4px;
  }
  .score-cell {
    .score-val {
      font-weight: 700;
      font-size: 15px;
    }
  }
}
</style>
