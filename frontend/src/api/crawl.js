/**
 * 数据采集 API
 */
import request from '@/utils/request'

/** 启动采集任务 */
export const startCrawl = (payload) => request.post('/crawl/start', payload)

/** 查询任务状态 */
export const getCrawlStatus = (taskId) => request.get(`/crawl/status/${taskId}`)

/** 采集日志 */
export const listCrawlLogs = (params) => request.get('/crawl/logs', { params })

/** 生成模拟数据 */
export const generateMockData = (params) => request.post('/crawl/mock', params)
