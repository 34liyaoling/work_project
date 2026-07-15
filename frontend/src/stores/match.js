/**
 * 匹配状态管理（Pinia）
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { matchWithJd, matchWithRole } from '@/api/match'

export const useMatchStore = defineStore('match', () => {
  const currentMode = ref('jd')             // jd / role
  const currentResult = ref(null)           // 单次匹配结果
  const topNResults = ref([])               // Top-N 排名
  const loading = ref(false)

  /** 与具体 JD 匹配 */
  const doMatchJd = async (payload) => {
    loading.value = true
    try {
      const data = await matchWithJd(payload)
      currentResult.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  /** 方向匹配 */
  const doMatchRole = async (payload) => {
    loading.value = true
    try {
      const data = await matchWithRole(payload)
      topNResults.value = data?.results || []
      return data
    } finally {
      loading.value = false
    }
  }

  return {
    currentMode,
    currentResult,
    topNResults,
    loading,
    doMatchJd,
    doMatchRole
  }
})
