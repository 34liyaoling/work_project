/**
 * 简历 API
 */
import request from '@/utils/request'

/** 简历列表 */
export const listResumes = (params) => request.get('/resume/', { params })

/** 简历详情 */
export const getResume = (resumeId) => request.get(`/resume/${resumeId}`)

/** 上传简历（FormData） */
export const uploadResume = (file, onProgress) => {
  const form = new FormData()
  form.append('file', file)
  return request.post('/resume/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded * 100) / e.total))
      }
    }
  })
}

/** 触发解析 */
export const parseResume = (resumeId, force = false) =>
  request.post(`/resume/${resumeId}/parse`, { force })

/** 获取简历技能 */
export const getResumeSkills = (resumeId) => request.get(`/resume/${resumeId}/skills`)
