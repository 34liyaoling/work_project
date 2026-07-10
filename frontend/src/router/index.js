import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layouts/MainLayout.vue'

const routes = [
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('../pages/Dashboard.vue'), meta: { title: '数据驾驶舱', icon: 'DataBoard' } },
      { path: 'graph-explorer', name: 'GraphExplorer', component: () => import('../pages/GraphExplorer.vue'), meta: { title: '图谱浏览器', icon: 'Share' } },
      { path: 'resume-analysis', name: 'ResumeAnalysis', component: () => import('../pages/ResumeAnalysis.vue'), meta: { title: '简历分析', icon: 'Document' } },
      { path: 'job-matching', name: 'JobMatching', component: () => import('../pages/JobMatching.vue'), meta: { title: '智能匹配', icon: 'Connection' } },
      { path: 'job-discovery', name: 'JobDiscovery', component: () => import('../pages/JobDiscovery.vue'), meta: { title: '新岗位发现', icon: 'Search' } },
      { path: 'gap-analysis', name: 'GapAnalysis', component: () => import('../pages/GapAnalysis.vue'), meta: { title: '差距分析', icon: 'TrendCharts' } },
      { path: 'career-path', name: 'CareerPath', component: () => import('../pages/CareerPath.vue'), meta: { title: '职业路径', icon: 'Guide' } },
      { path: 'market-intelligence', name: 'MarketIntelligence', component: () => import('../pages/MarketIntelligence.vue'), meta: { title: '市场情报', icon: 'DataAnalysis' } },
      { path: 'what-if-analysis', name: 'WhatIfAnalysis', component: () => import('../pages/WhatIfAnalysis.vue'), meta: { title: 'What-If分析', icon: 'SetUp' } },
      { path: 'batch-analysis', name: 'BatchAnalysis', component: () => import('../pages/BatchAnalysis.vue'), meta: { title: '批量分析', icon: 'Files' } },
      { path: 'qa-assistant', name: 'QaAssistant', component: () => import('../pages/QaAssistant.vue'), meta: { title: '智能问答', icon: 'ChatDotSquare' } },
      { path: 'admin-panel', name: 'AdminPanel', component: () => import('../pages/AdminPanel.vue'), meta: { title: '系统管理', icon: 'Setting' } },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
