import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useAppStore = defineStore('app', () => {
  const collapsed = ref(false)

  // ===== 页面级数据缓存（切换页面不丢失） =====
  const caches = ref({
    dashboard: { stats: null, skills: null, domains: null, jobs: null },
    graphExplorer: { nodes: [], edges: [] },
    jobDiscovery: { jobs: [], discovering: false },
    jobMatching: { results: [], matching: false, resumeList: [], domainList: [] },
    resumeAnalysis: { profile: null, parsedResumes: {} },
    gapAnalysis: { result: null },
    careerPath: { paths: [], roles: [] },
    whatIf: { result: null },
    marketIntel: { data: null },
    batchAnalysis: { result: null },
    qaAssistant: { messages: [] },
  })

  // ===== 全局请求状态（跨页面持久化） =====
  // 记录正在进行的异步操作，切换页面后回来可恢复结果
  const activeRequests = ref(new Map())

  function toggleSidebar() {
    collapsed.value = !collapsed.value
  }

  /**
   * 带缓存的 API 请求封装
   * - 如果缓存中有有效数据且 forceRefresh=false，直接返回缓存
   * - 否则发起请求，完成后写入缓存
   * - 请求进行中时标记状态，支持跨页面等待
   */
  async function cachedRequest(cacheKey, requestFn, options = {}) {
    const { forceRefresh = false } = options

    if (!forceRefresh && caches.value[cacheKey]?._data) {
      return caches.value[cacheKey]._data
    }

    try {
      const requestId = `${cacheKey}_${Date.now()}`
      activeRequests.value.set(requestId, { status: 'pending', cacheKey })

      const result = await requestFn()
      caches.value[cacheKey] = { ...caches.value[cacheKey], _data: result }
      activeRequests.value.delete(requestId)
      return result
    } catch (error) {
      activeRequests.value.forEach((v, k) => {
        if (v.cacheKey === cacheKey) activeRequests.value.delete(k)
      })
      throw error
    }
  }

  /** 设置页面缓存数据 */
  function setCache(key, data) {
    caches.value[key] = { ...caches.value[key], ...data }
  }

  /** 获取页面缓存 */
  function getCache(key) {
    return caches.value[key]
  }

  /** 清除指定页面缓存 */
  function clearCache(key) {
    if (caches.value[key]) {
      caches.value[key] = { _data: null }
    }
  }

  /** 某个请求是否正在进行中 */
  function isRequestActive(cacheKey) {
    for (const [, v] of activeRequests.value) {
      if (v.cacheKey === cacheKey) return true
    }
    return false
  }

  return {
    collapsed,
    caches,
    activeRequests,
    toggleSidebar,
    cachedRequest,
    setCache,
    getCache,
    clearCache,
    isRequestActive,
  }
})
