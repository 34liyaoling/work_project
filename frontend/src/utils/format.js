/**
 * 通用格式化工具
 */
import dayjs from 'dayjs'

/**
 * 格式化日期时间
 * @param {string|Date|number} date 日期
 * @param {string} pattern 模式，默认 YYYY-MM-DD HH:mm:ss
 */
export const formatDateTime = (date, pattern = 'YYYY-MM-DD HH:mm:ss') => {
  if (!date) return '-'
  return dayjs(date).format(pattern)
}

/**
 * 格式化日期（仅日期部分）
 */
export const formatDate = (date) => formatDateTime(date, 'YYYY-MM-DD')

/**
 * 相对时间（如：3 分钟前）
 */
export const fromNow = (date) => {
  if (!date) return '-'
  const now = Date.now()
  const t = new Date(date).getTime()
  const diff = Math.floor((now - t) / 1000)
  if (diff < 60) return `${diff} 秒前`
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 86400 * 30) return `${Math.floor(diff / 86400)} 天前`
  return formatDate(date)
}

/**
 * 百分比格式化（0.873 → "87.3%"）
 */
export const formatPercent = (val, digits = 1) => {
  if (val === null || val === undefined || isNaN(val)) return '-'
  return `${(Number(val) * 100).toFixed(digits)}%`
}

/**
 * 文件大小格式化
 */
export const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let n = Number(bytes)
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024
    i++
  }
  return `${n.toFixed(1)} ${units[i]}`
}

/**
 * 截断文本
 */
export const truncate = (text, max = 80) => {
  if (!text) return ''
  if (text.length <= max) return text
  return text.slice(0, max) + '...'
}

/**
 * 匹配率颜色（用于显示分值）
 */
export const scoreColor = (score) => {
  const s = Number(score) || 0
  if (s >= 0.8) return '#10b981'  // 绿
  if (s >= 0.6) return '#3b82f6'  // 蓝
  if (s >= 0.4) return '#f59e0b'  // 黄
  return '#ef4444'                // 红
}

/**
 * 数组转字典
 */
export const toMap = (arr, keyField = 'id') => {
  const map = {}
  for (const item of arr || []) {
    if (item && item[keyField] !== undefined) {
      map[item[keyField]] = item
    }
  }
  return map
}

export default {
  formatDateTime,
  formatDate,
  fromNow,
  formatPercent,
  formatFileSize,
  truncate,
  scoreColor,
  toMap
}
