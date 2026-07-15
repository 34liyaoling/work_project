<template>
  <div ref="container" class="graph-canvas"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { Graph } from '@antv/g6'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] }
})
const emit = defineEmits(['node-click'])

const container = ref(null)
let graph = null
let resizeObserver = null

/** 初始化 G6 图 */
const initGraph = () => {
  if (!container.value) return
  if (graph) {
    graph.destroy()
    graph = null
  }
  const width = container.value.clientWidth || 800
  const height = container.value.clientHeight || 600

  graph = new Graph({
    container: container.value,
    width,
    height,
    autoFit: 'view',
    background: '#fafbfc',
    data: {
      nodes: props.nodes,
      edges: props.edges
    },
    node: {
      type: 'circle',
      style: {
        size: (d) => {
          const p = d.data?.popularity ?? 0
          return 20 + Math.min(40, p * 40)
        },
        fill: (d) => colorByType(d.data?.type || d.data?.category),
        stroke: '#fff',
        lineWidth: 2,
        labelText: (d) => d.id,
        labelFill: '#1f2937',
        labelFontSize: 12,
        labelPlacement: 'bottom',
        labelBackground: true,
        labelBackgroundFill: '#fff',
        labelBackgroundOpacity: 0.85,
        labelPadding: [2, 4, 2, 4]
      }
    },
    edge: {
      type: 'line',
      style: {
        stroke: '#94a3b8',
        lineWidth: 1,
        endArrow: true,
        endArrowSize: 8,
        endArrowFill: '#94a3b8',
        curve: true
      }
    },
    layout: {
      type: 'force',
      preventOverlap: true,
      nodeStrength: -120,
      edgeStrength: 0.5,
      linkDistance: 120
    },
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element', 'click-select']
  })

  graph.render()

  // 节点点击
  graph.on('node:click', (evt) => {
    const id = evt.target?.id
    emit('node-click', { id })
  })
}

const colorByType = (type) => {
  const map = {
    jobrole: '#3b82f6',
    skill: '#10b981',
    tool: '#f59e0b',
    industry: '#8b5cf6',
    'AI': '#10b981',
    '编程语言': '#3b82f6',
    '前端框架': '#06b6d4',
    '数据库': '#ef4444'
  }
  return map[type] || '#94a3b8'
}

const fitView = () => graph?.fitView?.()
const zoomIn = () => {
  if (graph) graph.zoomBy(1.2)
}
const zoomOut = () => {
  if (graph) graph.zoomBy(0.8)
}

defineExpose({ fitView, zoomIn, zoomOut })

watch(
  () => [props.nodes, props.edges],
  async () => {
    await nextTick()
    if (graph) {
      graph.setData({ nodes: props.nodes, edges: props.edges })
    }
  }
)

onMounted(() => {
  initGraph()
  // 自适应大小
  if (window.ResizeObserver && container.value) {
    resizeObserver = new ResizeObserver(() => {
      if (graph && container.value) {
        graph.setSize(container.value.clientWidth, container.value.clientHeight)
      }
    })
    resizeObserver.observe(container.value)
  }
})

onBeforeUnmount(() => {
  if (graph) {
    graph.destroy()
    graph = null
  }
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})
</script>

<style lang="scss" scoped>
.graph-canvas {
  width: 100%;
  height: 100%;
  min-height: 600px;
  background: #fafbfc;
  border-radius: 6px;
  overflow: hidden;
}
</style>
