/**
 * axios 统一请求封装
 * - 自动注入 baseURL
 * - 拦截 401/500 等错误
 * - 统一处理后端 CommonResponse 格式（{code, message, data}）
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器：可注入 token 等
service.interceptors.request.use(
  (config) => {
    // 这里可加 token 注入
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：拆出 data，弹错误提示
service.interceptors.response.use(
  (response) => {
    const { data } = response
    // 后端约定的 CommonResponse 格式
    if (data && typeof data === 'object' && 'code' in data) {
      if (data.code !== 0) {
        ElMessage.error(data.message || '请求失败')
        return Promise.reject(new Error(data.message || '请求失败'))
      }
      return data.data
    }
    // 否则直接返回数据
    return data
  },
  (error) => {
    const status = error?.response?.status
    let msg = '网络异常'
    if (status === 401) {
      msg = '未授权，请重新登录'
    } else if (status === 403) {
      msg = '无访问权限'
    } else if (status === 404) {
      msg = '资源不存在'
    } else if (status === 500) {
      msg = '服务器内部错误'
    } else if (error?.message) {
      msg = error.message
    }
    ElMessage.error(msg)
    return Promise.reject(new Error(msg))
  }
)

export default service
