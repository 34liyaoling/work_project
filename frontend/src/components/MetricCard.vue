<template>
  <el-card shadow="never" class="metric-card" :body-style="{ padding: '16px' }">
    <div class="metric-inner">
      <div class="metric-info">
        <div class="metric-label">{{ title }}</div>
        <div class="metric-value" :style="{ color: color }">{{ value }}</div>
        <div v-if="subtitle" class="metric-subtitle">{{ subtitle }}</div>
      </div>
      <div v-if="icon" class="metric-icon" :style="{ background: color + '15', color }">
        <el-icon :size="28"><component :is="icon" /></el-icon>
      </div>
    </div>
  </el-card>
</template>

<script setup>
defineProps({
  title: String,
  value: [String, Number],
  subtitle: String,
  icon: String,
  color: { type: String, default: '#409eff' }
})
</script>

<style scoped>
.metric-card { border-radius: 8px; border: 1px solid var(--border-color); }
.metric-inner { display: flex; justify-content: space-between; align-items: center; }
.metric-label { font-size: 13px; color: var(--text-secondary); margin-bottom: 4px; }
.metric-value { font-size: 28px; font-weight: 700; line-height: 1.2; }
.metric-subtitle { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.metric-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
</style>
