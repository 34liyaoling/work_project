/**
 * 岗位管理 API
 */
import request from '@/utils/request'

/** 岗位列表 */
export const listRoles = (params) => request.get('/role/', { params })

/** 新岗位发现列表 */
export const listNewRoles = (params) => request.get('/role/new', { params })

/** 既有岗位更新列表 */
export const listRoleUpdates = (params) => request.get('/role/updates', { params })

/** 岗位详情 */
export const getRole = (roleId) => request.get(`/role/${roleId}`)

/** 审核岗位 */
export const reviewRole = (roleId, payload) => request.post(`/role/${roleId}/review`, payload)

/** 审核队列 */
export const getAuditQueue = (params) => request.get('/role/audit/queue', { params })

/** 触发岗位发现 */
export const triggerDiscovery = (payload) => request.post('/role/discover', payload)
