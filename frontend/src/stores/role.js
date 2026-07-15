/**
 * 岗位管理状态（Pinia）
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listNewRoles,
  listRoleUpdates,
  getAuditQueue,
  reviewRole,
  triggerDiscovery
} from '@/api/role'

export const useRoleStore = defineStore('role', () => {
  const newRoles = ref([])
  const updatedRoles = ref([])
  const auditQueue = ref([])
  const loading = ref(false)

  const loadNewRoles = async (params = {}) => {
    loading.value = true
    try {
      const data = await listNewRoles(params)
      newRoles.value = data?.items || []
    } finally {
      loading.value = false
    }
  }

  const loadUpdates = async (params = {}) => {
    loading.value = true
    try {
      const data = await listRoleUpdates(params)
      updatedRoles.value = data?.items || []
    } finally {
      loading.value = false
    }
  }

  const loadAuditQueue = async (params = {}) => {
    loading.value = true
    try {
      const data = await getAuditQueue(params)
      auditQueue.value = data?.items || []
    } finally {
      loading.value = false
    }
  }

  const doReview = async (roleId, payload) => {
    await reviewRole(roleId, payload)
    // 审核后从新岗位列表移除
    newRoles.value = newRoles.value.filter((r) => r.role_id !== roleId)
  }

  const triggerJobDiscovery = async (payload) => {
    return triggerDiscovery(payload)
  }

  return {
    newRoles,
    updatedRoles,
    auditQueue,
    loading,
    loadNewRoles,
    loadUpdates,
    loadAuditQueue,
    doReview,
    triggerJobDiscovery
  }
})
