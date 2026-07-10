<template>
  <div class="page-container">
    <div class="page-header">
      <h2>市场情报</h2>
      <p>基于知识图谱分析各技术领域的市场需求与技能趋势</p>
    </div>

    <div class="domain-cards">
      <div
        v-for="d in domains"
        :key="d"
        class="domain-card"
        :class="{ active: selectedDomain === d }"
        @click="selectDomain(d)"
      >
        <span class="domain-icon">{{ domainIcon(d) }}</span>
        <span class="domain-name">{{ d }}</span>
      </div>
    </div>

    <template v-if="marketData">
      <el-row :gutter="16">
        <el-col :span="14">
          <el-card shadow="never" class="chart-card">
            <template #header>
              <div class="card-header">
                <span>需求趋势</span>
                <el-tag type="info" size="small">近 12 个月</el-tag>
              </div>
            </template>
            <div ref="trendChartRef" class="chart-box"></div>
          </el-card>
        </el-col>
        <el-col :span="10">
          <el-card shadow="never" class="chart-card">
            <template #header>
              <div class="card-header">
                <span>城市需求排行 TOP10</span>
              </div>
            </template>
            <div ref="cityChartRef" class="chart-box"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="never" class="table-card">
        <template #header>
          <div class="card-header">
            <span>热门技能</span>
            <el-tag type="info" size="small">{{ marketData.hotSkills?.length || 0 }} 项</el-tag>
          </div>
        </template>
        <el-table :data="marketData.hotSkills || []" stripe style="width: 100%" size="small">
          <el-table-column prop="name" label="技能名称" min-width="150" />
          <el-table-column prop="demand" label="需求数量" width="120" sortable />
          <el-table-column prop="trend" label="趋势方向" width="110">
            <template #default="{ row }">
              <el-tag :type="trendType(row.trend)" size="small">
                {{ row.trend }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="salaryRange" label="薪资范围" width="160" />
        </el-table>
      </el-card>
    </template>

    <div v-else class="empty-state">
      <el-icon><DataAnalysis /></el-icon>
      <p>请在上方选择一个技术领域查看市场情报数据</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '../api'

const domains = ['人工智能', '大数据', '云计算', '软件开发', '物联网', '网络安全', '区块链', 'DevOps']

const selectedDomain = ref('')
const marketData = ref(null)

const trendChartRef = ref(null)
const cityChartRef = ref(null)
let trendChart = null
let cityChart = null

function domainIcon(d) {
  const map = {
    '人工智能': '🤖',
    '大数据': '📊',
    '云计算': '☁️',
    '软件开发': '💻',
    '物联网': '🔗',
    '网络安全': '🛡️',
    '区块链': '⛓️',
    'DevOps': '🔄'
  }
  return map[d] || '📌'
}

function trendType(t) {
  if (t === '上升') return 'success'
  if (t === '平稳') return 'info'
  if (t === '下降') return 'danger'
  return 'info'
}

function initCharts() {
  if (!marketData.value) return

  if (trendChartRef.value) {
    trendChart?.dispose()
    trendChart = echarts.init(trendChartRef.value)
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: marketData.value.trendMonths,
        axisLabel: { fontSize: 11 }
      },
      yAxis: { type: 'value', name: '需求指数' },
      series: [{
        type: 'line',
        data: marketData.value.trendData,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#409eff', width: 2 },
        itemStyle: { color: '#409eff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64,158,255,0.25)' },
            { offset: 1, color: 'rgba(64,158,255,0.02)' }
          ])
        }
      }]
    })
  }

  if (cityChartRef.value) {
    cityChart?.dispose()
    cityChart = echarts.init(cityChartRef.value)
    cityChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: marketData.value.cities,
        axisLabel: { fontSize: 11 }
      },
      yAxis: { type: 'value', name: '岗位数量' },
      series: [{
        type: 'bar',
        data: marketData.value.cityData,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#e6a23c' },
            { offset: 1, color: '#f4d19b' }
          ])
        },
        barWidth: '55%'
      }]
    })
  }
}

async function selectDomain(d) {
  selectedDomain.value = d
  marketData.value = null
  try {
    const res = await api.getMarketIntel(d)
    marketData.value = res || null
  } catch (e) {
    console.error('获取市场情报失败:', e)
    marketData.value = null
  }
  await nextTick()
  initCharts()
}

function handleResize() {
  trendChart?.resize()
  cityChart?.resize()
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  cityChart?.dispose()
})
</script>

<style scoped>
.domain-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 24px;
}

.domain-card {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-color);
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.domain-card:hover {
  border-color: #409eff;
  color: #409eff;
}

.domain-card.active {
  border-color: #409eff;
  background: #ecf5ff;
  color: #409eff;
  font-weight: 600;
}

.domain-icon {
  font-size: 18px;
}

.domain-name {
  font-size: 14px;
}

.chart-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
  margin-bottom: 16px;
}

.chart-box {
  width: 100%;
  height: 320px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 15px;
}

.table-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
  margin-top: 8px;
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
