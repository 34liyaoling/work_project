<template>
  <div class="page-container">
    <div class="page-header">
      <h2>数据驾驶舱</h2>
      <p>知识图谱全域数据概览与核心指标监控</p>
    </div>

    <div class="stat-cards">
      <MetricCard
        title="技能节点"
        :value="stats.skills"
        subtitle="全领域技能总数"
        icon="TrendCharts"
        color="#409eff"
      />
      <MetricCard
        title="岗位节点"
        :value="stats.jobs"
        subtitle="已收录岗位数量"
        icon="Briefcase"
        color="#67c23a"
      />
      <MetricCard
        title="关系边"
        :value="stats.relationships"
        subtitle="节点间关联数量"
        icon="Connection"
        color="#e6a23c"
      />
      <MetricCard
        title="领域分类"
        :value="stats.domains"
        subtitle="技术领域覆盖数"
        icon="Grid"
        color="#f56c6c"
      />
    </div>

    <div class="chart-grid">
      <div class="chart-card">
        <h3>技能趋势分布</h3>
        <div ref="trendChartRef" class="chart-box"></div>
      </div>
      <div class="chart-card">
        <h3>领域分布饼图</h3>
        <div ref="domainChartRef" class="chart-box"></div>
      </div>
      <div class="chart-card">
        <h3>城市需求 TOP10</h3>
        <div ref="cityChartRef" class="chart-box"></div>
      </div>
      <div class="chart-card">
        <h3>技能生命周期分布</h3>
        <div ref="lifecycleChartRef" class="chart-box"></div>
      </div>
    </div>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span>操作日志</span>
          <el-tag type="info" size="small">近 24 小时</el-tag>
        </div>
      </template>
      <el-table v-if="logs.length > 0" :data="logs" stripe style="width: 100%" size="small">
        <el-table-column prop="time" label="时间" width="180" />
        <el-table-column prop="action" label="操作" width="160" />
        <el-table-column prop="target" label="对象" width="160" />
        <el-table-column prop="user" label="操作人" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '成功' ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detail" label="详情" />
      </el-table>
      <div v-else class="empty-logs">暂无操作日志，请先执行数据采集或图谱构建操作</div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import MetricCard from '@/components/MetricCard.vue'
import api from '../api'

const trendChartRef = ref(null)
const domainChartRef = ref(null)
const cityChartRef = ref(null)
const lifecycleChartRef = ref(null)

let trendChart = null
let domainChart = null
let cityChart = null
let lifecycleChart = null

const stats = ref({
  skills: 0,
  jobs: 0,
  relationships: 0,
  domains: 0
})

const logs = ref([])

// 从 API 获取的真实数据
let rawStatsData = null
let rawJobsData = []
let rawSkillsData = []

function initTrendChart() {
  if (!trendChartRef.value) return

  trendChart = echarts.init(trendChartRef.value)

  // 从真实技能数据构建图表
  const skillMap = {}
  rawSkillsData.forEach(s => {
    const domain = s.domain || s.category || '其他'
    skillMap[domain] = (skillMap[domain] || 0) + 1
  })

  const categories = Object.keys(skillMap)
  const values = Object.values(skillMap)

  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: categories.length > 0 ? categories : ['暂无数据'],
      axisLabel: { fontSize: 11 }
    },
    yAxis: { type: 'value', name: '技能数量' },
    series: [{
      type: 'bar',
      data: values.length > 0 ? values : [0],
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#409eff' },
          { offset: 1, color: '#79bbff' }
        ])
      },
      barWidth: '50%'
    }]
  })
}

function initDomainChart() {
  if (!domainChartRef.value) return

  domainChart = echarts.init(domainChartRef.value)

  // 从真实数据统计各领域岗位数
  const domainMap = {}
  rawJobsData.forEach(j => {
    const d = j.domain || j.category || '未分类'
    domainMap[d] = (domainMap[d] || 0) + 1
  })

  const pieData = Object.entries(domainMap).map(([name, value]) => ({
    value,
    name
  }))

  // 如果没有数据则显示空状态
  if (pieData.length === 0) {
    pieData.push({ value: 1, name: '暂无数据' })
  }

  domainChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '50%'],
      avoidLabelOverlap: false,
      label: { show: true, formatter: '{b}\n{d}%', fontSize: 11 },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
      data: pieData
    }]
  })
}

function initCityChart() {
  if (!cityChartRef.value) return

  cityChart = echarts.init(cityChartRef.value)

  // 从真实岗位数据提取城市信息（如果有的话）
  const cityMap = {}
  rawJobsData.forEach(j => {
    const city = j.city || j.location || ''
    if (city) {
      cityMap[city] = (cityMap[city] || 0) + 1
    }
  })

  const cities = Object.entries(cityMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)

  if (cities.length > 0) {
    cityChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: cities.map(c => c[0]),
        axisLabel: { fontSize: 11 }
      },
      yAxis: { type: 'value', name: '岗位数量' },
      series: [{
        type: 'bar',
        data: cities.map(c => c[1]),
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#67c23a' },
            { offset: 1, color: '#95d475' }
          ])
        },
        barWidth: '50%'
      }]
    })
  } else {
    cityChart.setOption({
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: ['暂无城市数据'] },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: [0], barWidth: '50%' }]
    })
  }
}

function initLifecycleChart() {
  if (!lifecycleChartRef.value) return

  lifecycleChart = echarts.init(lifecycleChartRef)

  // 基于真实数据的技能阶段分布
  const stageMap = {新兴: 0, 成长: 0, 成熟: 0, 衰退: 0, 过时: 0}
  rawSkillsData.forEach(s => {
    const stage = s.lifecycle_stage || s.stage || '成熟'
    if (stageMap[stage] !== undefined) {
      stageMap[stage]++
    } else {
      stageMap['成熟']++
    }
  })

  const stages = Object.keys(stageMap)
  const counts = stages.map(s => stageMap[s])

  lifecycleChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (params) => `${params.name}<br/>技能数: ${params.value}`
    },
    grid: { left: '3%', right: '8%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: stages,
      axisLabel: { fontSize: 11 },
      splitLine: { show: false }
    },
    yAxis: [
      { type: 'value', name: '技能数量', position: 'left' }
    ],
    series: [
      {
        name: '技能数量',
        type: 'bar',
        yAxisIndex: 0,
        data: counts,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: (params) => {
            const colors = ['#f56c6c', '#e6a23c', '#409eff', '#909399', '#c0c4cc']
            return colors[params.dataIndex]
          }
        },
        barWidth: '50%'
      }
    ],
    legend: { data: ['技能数量'], bottom: 0, left: 'center' }
  })
}

async function loadDashboardData() {
  try {
    // 并行请求所有需要的数据
    const [statsRes, jobsRes, skillsRes] = await Promise.allSettled([
      api.getGraphStats(),
      api.getJobs(),
      api.getSkills()
    ])

    // 处理统计数据
    if (statsRes.status === 'fulfilled' && statsRes.value) {
      rawStatsData = statsRes.value
      const data = statsRes.value.data || statsRes.value
      stats.value = {
        skills: data.stats?.skill_nodes ?? data.skill_count ?? rawSkillsData.length ?? 0,
        jobs: data.job_count ?? rawJobsData.length ?? 0,
        relationships: data.stats?.total_relations ?? data.stats?.total_edges ?? 0,
        domains: data.domains?.length ?? 0,
      }
    }

    // 处理岗位数据
    if (jobsRes.status === 'fulfilled' && jobsRes.value) {
      rawJobsData = jobsRes.value.jobs || jobsRes.value.data?.jobs || []
    }

    // 处理技能数据
    if (skillsRes.status === 'fulfilled' && skillsRes.value) {
      rawSkillsData = skillsRes.value.skills || skillsRes.value.data?.skills || []
    }

  } catch (error) {
    console.error('Dashboard 数据加载失败:', error)
  }
}

function handleResize() {
  trendChart?.resize()
  domainChart?.resize()
  cityChart?.resize()
  lifecycleChart?.resize()
}

onMounted(async () => {
  await loadDashboardData()
  await nextTick()
  initTrendChart()
  initDomainChart()
  initCityChart()
  initLifecycleChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  domainChart?.dispose()
  cityChart?.dispose()
  lifecycleChart?.dispose()
})
</script>

<style scoped>
.chart-box {
  width: 100%;
  height: 300px;
}

.table-card {
  border-radius: 8px;
  border: 1px solid var(--border-color);
  margin-top: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  font-size: 15px;
}

.empty-logs {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
