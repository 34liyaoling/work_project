/**
 * API 统一导出
 */
import request from '@/utils/request'

export const checkApiHealth = () => request.get('/health/live')
