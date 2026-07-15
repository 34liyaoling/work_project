/**
 * JD API
 */
import request from '@/utils/request'

/** 分页查询 JD */
export const listJds = (params) => request.get('/jd/', { params })

/** 获取 JD 详情 */
export const getJd = (jdId) => request.get(`/jd/${jdId}`)

/** 创建 JD */
export const createJd = (payload) => request.post('/jd/', payload)

/** 触发 JD 解析 */
export const parseJd = (jdId) => request.post(`/jd/${jdId}/parse`)

/** 批量解析 */
export const batchParseJds = (jdIds, force = false) =>
  request.post('/jd/batch_parse', { jd_ids: jdIds, force })

/** 删除 JD */
export const deleteJd = (jdId) => request.delete(`/jd/${jdId}`)
