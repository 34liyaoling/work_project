<template>
  <div class="home-view">
    <div class="hero">
      <div class="hero-inner">
        <h1>多源异构数据驱动的岗位与能力图谱</h1>
        <p class="subtitle">
          从拉勾 / Boss直聘 / 猎聘 等渠道自动采集 JD 与简历，构建动态演化的技能图谱，
          提供精准的人岗匹配与岗位发现能力。
        </p>
        <div class="cta">
          <el-button type="primary" size="large" @click="$router.push('/graph')">
            <el-icon><DataLine /></el-icon>
            <span>查看全景图谱</span>
          </el-button>
          <el-button size="large" @click="$router.push('/match')">
            <el-icon><Aim /></el-icon>
            <span>开始人岗匹配</span>
          </el-button>
          <el-button size="large" @click="$router.push('/role')">
            <el-icon><Management /></el-icon>
            <span>岗位管理</span>
          </el-button>
        </div>
      </div>
    </div>

    <!-- 三大功能卡 -->
    <el-row :gutter="20" class="feature-row">
      <el-col :span="8">
        <el-card class="feature-card" shadow="hover" @click="$router.push('/graph')">
          <div class="icon" style="background:#dbeafe;color:#1e40af">
            <el-icon size="32"><Share /></el-icon>
          </div>
          <h3>全景图谱</h3>
          <p>基于 AntV G6 渲染技能级粒度的交互图谱，支持技术栈 / 级别 / 领域多视图切换，技能依赖链、动态演化时间线。</p>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="feature-card" shadow="hover" @click="$router.push('/match')">
          <div class="icon" style="background:#fef3c7;color:#92400e">
            <el-icon size="32"><Aim /></el-icon>
          </div>
          <h3>人岗匹配诊断</h3>
          <p>双模式匹配：与具体 JD 精准匹配 / 与岗位方向 Top-N 排名。包含分维度评分、技能差距、学习路径建议。</p>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="feature-card" shadow="hover" @click="$router.push('/role')">
          <div class="icon" style="background:#dcfce7;color:#166534">
            <el-icon size="32"><Management /></el-icon>
          </div>
          <h3>岗位管理</h3>
          <p>新岗位发现、既有岗位动态更新、人工审核队列。保障岗位定义的准确性与时效性。</p>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据概览 -->
    <el-row :gutter="20" class="mt-24">
      <el-col :span="24">
        <el-card class="section-card">
          <template #header>
            <div class="card-header">
              <span>系统数据概览</span>
              <el-button text @click="loadStats">
                <el-icon><Refresh /></el-icon>
                <span>刷新</span>
              </el-button>
            </div>
          </template>
          <el-row :gutter="20">
            <el-col :span="6">
              <div class="metric-box">
                <div class="metric-label">JD 总数</div>
                <div class="metric-value">{{ stats.jd_count }}</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="metric-box">
                <div class="metric-label">简历总数</div>
                <div class="metric-value">{{ stats.resume_count }}</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="metric-box">
                <div class="metric-label">岗位定义</div>
                <div class="metric-value">{{ stats.role_count }}</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="metric-box">
                <div class="metric-label">匹配记录</div>
                <div class="metric-value">{{ stats.match_count }}</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷操作 -->
    <el-row :gutter="20" class="mt-24">
      <el-col :span="12">
        <el-card>
          <template #header><span>生成模拟数据</span></template>
          <p class="text-muted">用于演示与压力测试：生成 JD、简历、岗位卡片。</p>
          <el-button type="success" @click="genMock" :loading="mocking">
            <el-icon><MagicStick /></el-icon>
            <span>一键生成</span>
          </el-button>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><span>赛题信息</span></template>
          <p><strong>赛题编号：</strong>XH-202621</p>
          <p><strong>发榜方：</strong>科大讯飞</p>
          <p><strong>主题：</strong>多源异构数据驱动岗位和能力图谱构建与动态演化分析</p>
          <p class="text-muted" style="margin-top:8px">三大核心：90% 解析准确率、动态图谱演化、双方式人岗匹配</p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listJds } from '@/api/jd'
import { listResumes } from '@/api/resume'
import { listRoles } from '@/api/role'
import { listMatches } from '@/api/match'
import { generateMockData } from '@/api/crawl'

const stats = ref({
  jd_count: 0,
  resume_count: 0,
  role_count: 0,
  match_count: 0
})
const mocking = ref(false)

const loadStats = async () => {
  try {
    const [jd, resume, role, match] = await Promise.allSettled([
      listJds({ page: 1, page_size: 1 }),
      listResumes({ page: 1, page_size: 1 }),
      listRoles({ page: 1, page_size: 1 }),
      listMatches({ page: 1, page_size: 1 })
    ])
    if (jd.status === 'fulfilled') stats.value.jd_count = jd.value?.pagination?.total ?? 0
    if (resume.status === 'fulfilled') stats.value.resume_count = resume.value?.pagination?.total ?? 0
    if (role.status === 'fulfilled') stats.value.role_count = role.value?.pagination?.total ?? 0
    if (match.status === 'fulfilled') stats.value.match_count = match.value?.pagination?.total ?? 0
  } catch (e) {
    console.error('加载统计失败', e)
  }
}

const genMock = async () => {
  mocking.value = true
  try {
    const res = await generateMockData({ jd_count: 50, resume_count: 20, role_count: 10 })
    ElMessage.success(
      `已生成 JD ${res.jd_created} 条、简历 ${res.resume_created} 份、岗位 ${res.role_created} 个`
    )
    await loadStats()
  } catch (e) {
    // request 拦截器已提示
  } finally {
    mocking.value = false
  }
}

onMounted(loadStats)
</script>

<style lang="scss" scoped>
.home-view {
  max-width: 1280px;
  margin: 0 auto;
}

.hero {
  background: linear-gradient(135deg, #1e3a8a 0%, #6d28d9 100%);
  color: #fff;
  border-radius: 16px;
  padding: 60px 40px;
  text-align: center;
  box-shadow: 0 8px 24px rgba(30, 58, 138, 0.18);

  h1 {
    font-size: 32px;
    margin: 0 0 16px;
    letter-spacing: 1px;
  }

  .subtitle {
    font-size: 15px;
    max-width: 720px;
    margin: 0 auto 28px;
    line-height: 1.7;
    color: rgba(255, 255, 255, 0.9);
  }

  .cta {
    display: flex;
    gap: 12px;
    justify-content: center;
    flex-wrap: wrap;
  }
}

.feature-row {
  margin-top: 32px;
}

.feature-card {
  cursor: pointer;
  transition: transform 0.2s ease;
  border: 1px solid #e2e8f0;
  &:hover { transform: translateY(-4px); }
  .icon {
    width: 56px;
    height: 56px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
  }
  h3 { margin: 0 0 8px; font-size: 18px; }
  p { margin: 0; color: #64748b; line-height: 1.6; font-size: 13px; }
}

.metric-box {
  text-align: center;
  padding: 16px;
  border-radius: 8px;
  background: #f8fafc;
  .metric-label { color: #64748b; font-size: 13px; }
  .metric-value { color: #1e3a8a; font-size: 28px; font-weight: 700; margin-top: 4px; }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
