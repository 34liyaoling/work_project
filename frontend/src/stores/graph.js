/**
 * 图谱状态管理（Pinia）
 * - 维护当前视图、节点、边、加载态
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { exportGraph, getGraphView, getSkillTimeline } from '@/api/graph'

export const useGraphStore = defineStore('graph', () => {
  // 状态
  const viewType = ref('default')         // default / technology_stack / level / domain
  const nodes = ref([])
  const edges = ref([])
  const viewItems = ref([])                // 当前视图的扁平列表
  const timeline = ref([])
  const selectedSkill = ref('')
  const loading = ref(false)
  const metadata = ref({})

  // 计算属性
  const nodeCount = computed(() => nodes.value.length)
  const edgeCount = computed(() => edges.value.length)

  /** 加载默认全图（供 G6 渲染） */
  const loadGraph = async (vt = 'default') => {
    viewType.value = vt
    loading.value = true
    try {
      const data = await exportGraph(vt)
      nodes.value = data?.nodes || []
      edges.value = data?.edges || []
      metadata.value = data?.metadata || {}
    } catch (e) {
      console.error('加载图谱失败', e)
    } finally {
      loading.value = false
    }
  }

  /** 加载多视图数据 */
  const loadView = async (vt, limit = 200) => {
    viewType.value = vt
    loading.value = true
    try {
      const data = await getGraphView(vt, limit)
      viewItems.value = data?.items || []
    } catch (e) {
      console.error('加载视图失败', e)
    } finally {
      loading.value = false
    }
  }

  /** 加载技能时间线 */
  const loadTimeline = async (skillName) => {
    selectedSkill.value = skillName
    if (!skillName) {
      timeline.value = []
      return
    }
    try {
      const data = await getSkillTimeline(skillName)
      timeline.value = data?.timeline || []
    } catch (e) {
      console.error('加载时间线失败', e)
      timeline.value = []
    }
  }

  return {
    viewType,
    nodes,
    edges,
    viewItems,
    timeline,
    selectedSkill,
    loading,
    metadata,
    nodeCount,
    edgeCount,
    loadGraph,
    loadView,
    loadTimeline
  }
})
