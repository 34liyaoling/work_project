<template>
  <el-card class="match-score">
    <template #header>
      <div class="card-header">
        <span>总体匹配率</span>
        <el-tag size="small" :type="tagType">{{ levelLabel }}</el-tag>
      </div>
    </template>
    <el-row :gutter="20" align="middle">
      <el-col :span="10">
        <v-chart class="gauge" :option="gaugeOption" autoresize />
      </el-col>
      <el-col :span="14">
        <div class="meta">
          <div class="meta-row">
            <span class="label">目标：</span>
            <span class="value">{{ result.target_name || result.target_id }}</span>
          </div>
          <div class="meta-row">
            <span class="label">简历：</span>
            <span class="value">{{ result.resume_id }}</span>
          </div>
          <div class="meta-row">
            <span class="label">必备技能：</span>
            <span class="value" :style="{ color: scoreColor(result.required_score) }">
              {{ formatPercent(result.required_score) }}
            </span>
          </div>
          <div class="meta-row">
            <span class="label">加分技能：</span>
            <span class="value" :style="{ color: scoreColor(result.preferred_score) }">
              {{ formatPercent(result.preferred_score) }}
            </span>
          </div>
          <div class="meta-row">
            <span class="label">技能深度：</span>
            <span class="value" :style="{ color: scoreColor(result.depth_score) }">
              {{ formatPercent(result.depth_score) }}
            </span>
          </div>
          <div class="meta-row">
            <span class="label">领域契合：</span>
            <span class="value" :style="{ color: scoreColor(result.domain_score) }">
              {{ formatPercent(result.domain_score) }}
            </span>
          </div>
        </div>
      </el-col>
    </el-row>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { GaugeChart } from 'echarts/charts'
import { formatPercent, scoreColor } from '@/utils/format'

use([CanvasRenderer, GaugeChart])

const props = defineProps({
  result: { type: Object, required: true }
})

const score = computed(() => Math.round((props.result.overall_score || 0) * 100))

const gaugeOption = computed(() => ({
  series: [
    {
      type: 'gauge',
      progress: { show: true, width: 18 },
      axisLine: { lineStyle: { width: 18 } },
      pointer: { width: 4 },
      axisTick: { show: false },
      splitLine: { length: 8, lineStyle: { width: 2, color: '#cbd5e1' } },
      axisLabel: { distance: 24, color: '#64748b', fontSize: 11 },
      anchor: { show: true, size: 8, itemStyle: { color: '#1e3a8a' } },
      title: { show: true, offsetCenter: [0, '70%'], color: '#64748b', fontSize: 13 },
      detail: {
        valueAnimation: true,
        fontSize: 32,
        color: scoreColor(props.result.overall_score),
        formatter: '{value}%',
        offsetCenter: [0, '0%']
      },
      data: [{ value: score.value, name: '总体匹配率' }]
    }
  ]
}))

const levelLabel = computed(() => {
  const s = props.result.overall_score || 0
  if (s >= 0.8) return '高度匹配'
  if (s >= 0.6) return '良好匹配'
  if (s >= 0.4) return '部分匹配'
  return '差距较大'
})

const tagType = computed(() => {
  const s = props.result.overall_score || 0
  if (s >= 0.8) return 'success'
  if (s >= 0.6) return 'primary'
  if (s >= 0.4) return 'warning'
  return 'danger'
})
</script>

<style lang="scss" scoped>
.match-score {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
  }
  .gauge { height: 240px; }
  .meta { display: flex; flex-direction: column; gap: 10px; }
  .meta-row {
    display: flex;
    align-items: center;
    .label { width: 100px; color: #64748b; font-size: 13px; }
    .value { font-weight: 600; font-size: 14px; }
  }
}
</style>
