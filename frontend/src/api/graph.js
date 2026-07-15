/**
 * 图谱 API
 */
import request from '@/utils/request'

/** 导出图谱（G6 渲染） */
export const exportGraph = (viewType = 'default') =>
  request.get('/graph/export', { params: { view_type: viewType } })

/** 多视图（technology_stack/level/domain） */
export const getGraphView = (viewType, limit = 200) =>
  request.get(`/graph/view/${viewType}`, { params: { limit } })

/** 技能依赖链 */
export const getSkillDependencies = (skillName, depth = 3) =>
  request.get(`/graph/skill/${encodeURIComponent(skillName)}/dependencies`, { params: { depth } })

/** 技能相关岗位 */
export const getRelatedJobs = (skillName, topN = 10) =>
  request.get(`/graph/skill/${encodeURIComponent(skillName)}/related_jobs`, { params: { top_n: topN } })

/** 技能时间线 */
export const getSkillTimeline = (skillName) =>
  request.get(`/graph/timeline/${encodeURIComponent(skillName)}`)

/** 岗位详情 */
export const getJobRole = (roleName) =>
  request.get(`/graph/jobrole/${encodeURIComponent(roleName)}`)

/** 创建快照 */
export const createSnapshot = (description) =>
  request.post('/graph/snapshot', { description })

/** 恢复快照 */
export const restoreSnapshot = (snapshotId) =>
  request.post(`/graph/snapshot/${snapshotId}/restore`)
