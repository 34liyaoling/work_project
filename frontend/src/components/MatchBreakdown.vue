<template>
  <el-card class="match-breakdown">
    <template #header><span>分维度匹配详情</span></template>
    <div v-for="item in result.breakdown || []" :key="item.dimension" class="dimension">
      <div class="dim-header">
        <span class="dim-name">{{ item.dimension }}</span>
        <span class="dim-score" :style="{ color: scoreColor(item.score) }">
          {{ formatPercent(item.score) }}
        </span>
        <span class="dim-weight">权重 {{ (item.weight * 100).toFixed(0) }}%</span>
      </div>
      <el-progress
        :percentage="Math.round((item.score || 0) * 100)"
        :stroke-width="8"
        :color="scoreColor(item.score)"
      />
      <div v-if="item.matched_skills?.length || item.missing_skills?.length" class="skills">
        <div v-if="item.matched_skills?.length" class="matched">
          <span class="label">已掌握：</span>
          <el-tag
            v-for="s in item.matched_skills"
            :key="s"
            type="success"
            size="small"
            effect="light"
          >{{ s }}</el-tag>
        </div>
        <div v-if="item.missing_skills?.length" class="missing mt-16">
          <span class="label">待补齐：</span>
          <el-tag
            v-for="s in item.missing_skills"
            :key="s"
            type="danger"
            size="small"
            effect="light"
          >{{ s }}</el-tag>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { formatPercent, scoreColor } from '@/utils/format'

defineProps({
  result: { type: Object, required: true }
})
</script>

<style lang="scss" scoped>
.match-breakdown {
  .dimension {
    padding: 12px 0;
    border-bottom: 1px dashed #e2e8f0;
    &:last-child { border-bottom: none; }
  }
  .dim-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
  }
  .dim-name { font-weight: 600; }
  .dim-score { font-size: 18px; font-weight: 700; margin-left: auto; }
  .dim-weight { color: #94a3b8; font-size: 12px; }
  .skills {
    margin-top: 10px;
    .label { color: #64748b; font-size: 12px; margin-right: 6px; }
    .el-tag { margin: 2px 4px 2px 0; }
  }
  .mt-16 { margin-top: 8px; }
}
</style>
