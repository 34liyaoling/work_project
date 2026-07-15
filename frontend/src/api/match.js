/**
 * 人岗匹配 API
 */
import request from '@/utils/request'

/** 与具体 JD 匹配 */
export const matchWithJd = (payload) => request.post('/match/jd', payload)

/** 与岗位方向匹配（Top-N） */
export const matchWithRole = (payload) => request.post('/match/role', payload)

/** 获取单次匹配记录 */
export const getMatch = (matchId) => request.get(`/match/${matchId}`)

/** 匹配历史 */
export const listMatches = (params) => request.get('/match/', { params })
