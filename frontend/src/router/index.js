/**
 * 路由配置
 * - /                首页
 * - /graph           全景图谱可视化
 * - /match           人岗匹配诊断
 * - /role            岗位管理（审核/发现/更新）
 */
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/graph',
    name: 'graph',
    component: () => import('@/views/GraphView.vue'),
    meta: { title: '全景图谱' }
  },
  {
    path: '/match',
    name: 'match',
    component: () => import('@/views/MatchView.vue'),
    meta: { title: '人岗匹配' }
  },
  {
    path: '/role',
    name: 'role',
    component: () => import('@/views/RoleView.vue'),
    meta: { title: '岗位管理' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/HomeView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  if (to.meta?.title) {
    document.title = `${to.meta.title} · CompetencyGraph`
  }
  next()
})

export default router
