<template>
  <el-container style="height: 100vh;">
    <el-aside :width="collapsed ? '64px' : '220px'" class="sidebar">
      <div class="logo-area" @click="router.push('/dashboard')">
        <span class="logo-icon">🧠</span>
        <span v-show="!collapsed" class="logo-text">知识图谱系统</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed"
        router
        background-color="#001529"
        text-color="#ffffffa0"
        active-text-color="#fff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon><template #title>数据驾驶舱</template>
        </el-menu-item>
        <el-menu-item index="/graph-explorer">
          <el-icon><Share /></el-icon><template #title>图谱浏览器</template>
        </el-menu-item>
        <el-menu-item index="/resume-analysis">
          <el-icon><Document /></el-icon><template #title>简历分析</template>
        </el-menu-item>
        <el-menu-item index="/job-matching">
          <el-icon><Connection /></el-icon><template #title>智能匹配</template>
        </el-menu-item>
        <el-menu-item index="/job-discovery">
          <el-icon><Search /></el-icon><template #title>新岗位发现</template>
        </el-menu-item>
        <el-menu-item index="/gap-analysis">
          <el-icon><TrendCharts /></el-icon><template #title>差距分析</template>
        </el-menu-item>
        <el-menu-item index="/career-path">
          <el-icon><Guide /></el-icon><template #title>职业路径</template>
        </el-menu-item>
        <el-menu-item index="/market-intelligence">
          <el-icon><DataAnalysis /></el-icon><template #title>市场情报</template>
        </el-menu-item>
        <el-menu-item index="/what-if-analysis">
          <el-icon><SetUp /></el-icon><template #title>What-If分析</template>
        </el-menu-item>
        <el-menu-item index="/batch-analysis">
          <el-icon><Files /></el-icon><template #title>批量分析</template>
        </el-menu-item>
        <el-menu-item index="/qa-assistant">
          <el-icon><ChatDotSquare /></el-icon><template #title>智能问答</template>
        </el-menu-item>
        <el-menu-item index="/admin-panel">
          <el-icon><Setting /></el-icon><template #title>系统管理</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="topbar">
        <div class="topbar-left">
          <el-button :icon="collapsed ? 'Expand' : 'Fold'" text @click="store.toggleSidebar()" />
          <span class="topbar-title">新一代信息技术全景图谱系统</span>
        </div>
        <div class="topbar-right">
          <el-tag type="info" size="small">v1.0</el-tag>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '../stores/app'

const route = useRoute()
const router = useRouter()
const store = useAppStore()
const collapsed = computed(() => store.collapsed)
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.sidebar {
  background: #001529;
  transition: width 0.3s;
  overflow: hidden;
}
.logo-area {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  cursor: pointer;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.logo-icon { font-size: 28px; margin-right: 8px; }
.logo-text { color: #fff; font-size: 16px; font-weight: 600; white-space: nowrap; }
.el-menu { border-right: none; }
.topbar {
  background: #fff;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
}
.topbar-left { display: flex; align-items: center; gap: 12px; }
.topbar-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.topbar-right { display: flex; align-items: center; gap: 8px; }
.main-content {
  background: var(--bg-light);
  padding: 0;
  overflow-y: auto;
}
</style>
