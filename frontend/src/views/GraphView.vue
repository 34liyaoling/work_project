<template>
  <div class="graph-view">
    <el-card class="control-bar">
      <div class="control-inner">
        <ViewSwitcher v-model="store.viewType" @change="onViewChange" />
        <el-input
          v-model="keyword"
          placeholder="搜索技能 / 岗位"
          clearable
          style="width: 240px"
          @input="onSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button @click="reload">
          <el-icon><Refresh /></el-icon>
          <span>刷新</span>
        </el-button>
        <el-tag size="small">节点: {{ store.nodeCount }}</el-tag>
        <el-tag size="small" type="success">边: {{ store.edgeCount }}</el-tag>
      </div>
    </el-card>

    <el-row :gutter="16" class="main-row">
      <!-- 图谱画布 -->
      <el-col :span="17">
        <el-card class="graph-card">
          <template #header>
            <div class="card-header">
              <span>技能级粒度图谱（{{ viewTitle }}）</span>
              <el-button-group>
                <el-button size="small" @click="zoomIn">
                  <el-icon><ZoomIn /></el-icon>
                </el-button>
                <el-button size="small" @click="zoomOut">
                  <el-icon><ZoomOut /></el-icon>
                </el-button>
                <el-button size="small" @click="fitView">适配</el-button>
              </el-button-group>
            </div>
          </template>
          <GraphCanvas
            ref="canvasRef"
            :nodes="filteredNodes"
            :edges="filteredEdges"
            @node-click="onNodeClick"
          />
        </el-card>
      </el-col>

      <!-- 时间线 -->
      <el-col :span="7">
        <TimelinePanel
          :skill-name="store.selectedSkill"
          :timeline="store.timeline"
        />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useGraphStore } from '@/stores/graph'
import ViewSwitcher from '@/components/ViewSwitcher.vue'
import GraphCanvas from '@/components/GraphCanvas.vue'
import TimelinePanel from '@/components/TimelinePanel.vue'

const store = useGraphStore()
const canvasRef = ref(null)
const keyword = ref('')

const viewTitle = computed(() => {
  return {
    default: '默认视图',
    technology_stack: '按技术栈',
    level: '按级别',
    domain: '按领域'
  }[store.viewType] || '图谱视图'
})

// 过滤节点/边
const filteredNodes = computed(() => {
  if (!keyword.value) return store.nodes
  const kw = keyword.value.toLowerCase()
  return store.nodes.filter((n) =>
    (n.label || n.id || '').toLowerCase().includes(kw)
  )
})

const filteredEdges = computed(() => {
  const ids = new Set(filteredNodes.value.map((n) => n.id))
  return store.edges.filter((e) => ids.has(e.source) && ids.has(e.target))
})

const onViewChange = (vt) => {
  store.loadGraph(vt)
}

const onSearch = () => {
  // 搜索由 computed 自动响应
}

const onNodeClick = (node) => {
  store.loadTimeline(node.id || node.label)
}

const reload = () => {
  store.loadGraph(store.viewType)
}

const zoomIn = () => canvasRef.value?.zoomIn?.()
const zoomOut = () => canvasRef.value?.zoomOut?.()
const fitView = () => canvasRef.value?.fitView?.()

onMounted(() => {
  store.loadGraph('default')
})
</script>

<style lang="scss" scoped>
.graph-view {
  max-width: 1600px;
  margin: 0 auto;
}

.control-bar {
  margin-bottom: 16px;
  .control-inner {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }
}

.main-row {
  min-height: 600px;
}

.graph-card {
  height: 720px;
  display: flex;
  flex-direction: column;
  :deep(.el-card__body) { flex: 1; min-height: 0; padding: 12px; }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
</style>
