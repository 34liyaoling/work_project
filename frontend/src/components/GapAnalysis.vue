<template>
  <el-card class="gap-analysis">
    <template #header>
      <div class="card-header">
        <span>技能差距分析</span>
        <el-tag size="small" type="danger">{{ gaps.length }} 项待补齐</el-tag>
      </div>
    </template>
    <el-empty v-if="!gaps || gaps.length === 0" description="无明显技能差距" />
    <div v-else class="gap-grid">
      <div
        v-for="(g, idx) in sortedGaps"
        :key="idx"
        class="gap-card"
        :class="severityClass(g)"
      >
        <div class="gap-header">
          <el-tag :type="statusTagType(g.status)" size="small">{{ statusText(g.status) }}</el-tag>
          <span class="importance">重要性 {{ (g.importance * 100).toFixed(0) }}%</span>
        </div>
        <div class="gap-skill">{{ g.skill_name }}</div>
        <div v-if="g.category" class="gap-category">{{ g.category }}</div>
        <div v-if="g.suggestion" class="gap-suggestion">
          <el-icon><InfoFilled /></el-icon>
          <span>{{ g.suggestion }}</span>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  gaps: { type: Array, default: () => [] }
})

const sortedGaps = computed(() => {
  return [...(props.gaps || [])].sort((a, b) => (b.importance || 0) - (a.importance || 0))
})

const statusText = (s) => {
  return { missing: '缺失', met: '已具备', exceeded: '已超越' }[s] || s
}

const statusTagType = (s) => {
  return { missing: 'danger', met: 'success', exceeded: 'primary' }[s] || 'info'
}

const severityClass = (g) => {
  if (g.status === 'missing' && g.importance >= 0.8) return 'severity-high'
  if (g.status === 'missing' && g.importance >= 0.5) return 'severity-medium'
  if (g.status === 'missing') return 'severity-low'
  return 'severity-ok'
}
</script>

<style lang="scss" scoped>
.gap-analysis {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
  }
  .gap-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 12px;
  }
  .gap-card {
    border: 1px solid #e2e8f0;
    border-left: 4px solid #cbd5e1;
    border-radius: 8px;
    padding: 12px;
    background: #fff;
    transition: transform 0.2s;
    &:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    .gap-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    .importance { color: #94a3b8; font-size: 12px; }
    .gap-skill { font-weight: 600; font-size: 15px; }
    .gap-category { color: #94a3b8; font-size: 12px; margin: 2px 0 6px; }
    .gap-suggestion {
      display: flex;
      gap: 4px;
      font-size: 12px;
      color: #475569;
      background: #f8fafc;
      padding: 6px 8px;
      border-radius: 4px;
      margin-top: 8px;
    }
    &.severity-high { border-left-color: #ef4444; background: #fef2f2; }
    &.severity-medium { border-left-color: #f59e0b; background: #fffbeb; }
    &.severity-low { border-left-color: #94a3b8; }
    &.severity-ok { border-left-color: #10b981; background: #f0fdf4; }
  }
}
</style>
