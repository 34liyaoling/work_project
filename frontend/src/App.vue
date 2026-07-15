<template>
  <el-container class="app-container">
    <!-- 顶栏 -->
    <el-header class="app-header">
      <div class="brand">
        <el-icon><Connection /></el-icon>
        <span class="title">CompetencyGraph</span>
        <el-tag size="small" type="info" effect="plain">XH-202621</el-tag>
      </div>
      <el-menu
        mode="horizontal"
        :default-active="activeMenu"
        router
        class="app-menu"
      >
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item index="/graph">全景图谱</el-menu-item>
        <el-menu-item index="/match">人岗匹配</el-menu-item>
        <el-menu-item index="/role">岗位管理</el-menu-item>
      </el-menu>
      <div class="user-area">
        <el-button text @click="checkHealth">
          <el-icon><CircleCheck /></el-icon>
          <span style="margin-left:4px">健康检查</span>
        </el-button>
      </div>
    </el-header>

    <!-- 主区域 -->
    <el-main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </el-main>

    <!-- 底栏 -->
    <el-footer class="app-footer" height="40px">
      <span>© 2026 科大讯飞 XH-202621 赛题 · 多源异构数据驱动的岗位与能力图谱</span>
    </el-footer>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { checkApiHealth } from '@/api/health'

const route = useRoute()
const activeMenu = computed(() => route.path)

const checkHealth = async () => {
  try {
    const res = await checkApiHealth()
    if (res?.status === 'ok') {
      ElMessage.success(`服务正常: ${res.service}`)
    } else {
      ElMessage.warning('服务状态异常')
    }
  } catch (e) {
    ElMessage.error(`健康检查失败: ${e?.message || e}`)
  }
}
</script>

<style lang="scss" scoped>
.app-container {
  min-height: 100vh;
  background: #f5f7fb;
}

.app-header {
  display: flex;
  align-items: center;
  background: linear-gradient(135deg, #1e3a8a 0%, #5b21b6 100%);
  color: #fff;
  padding: 0 24px;
  height: 60px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;

  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 18px;
    font-weight: 600;

    .title {
      letter-spacing: 1px;
    }
  }

  .app-menu {
    flex: 1;
    margin-left: 40px;
    background: transparent;
    border-bottom: none;

    :deep(.el-menu-item) {
      color: rgba(255, 255, 255, 0.85);
      &:hover, &.is-active {
        color: #fff;
        background: rgba(255, 255, 255, 0.12) !important;
      }
    }
  }

  .user-area {
    color: #fff;
  }
}

.app-main {
  padding: 24px;
  min-height: calc(100vh - 100px);
}

.app-footer {
  text-align: center;
  color: #94a3b8;
  font-size: 12px;
  line-height: 40px;
  background: #fff;
  border-top: 1px solid #e2e8f0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
