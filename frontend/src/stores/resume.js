import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_KEY = 'kg_resume_context'

export const useResumeStore = defineStore('resume', () => {
  const saved = (() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      return raw ? JSON.parse(raw) : {}
    } catch {
      return {}
    }
  })()

  const resumeId = ref(saved.resumeId || '')
  const candidateName = ref(saved.candidateName || '')
  const skills = ref(saved.skills || [])
  const credibilityScore = ref(saved.credibilityScore ?? null)

  function _persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        resumeId: resumeId.value,
        candidateName: candidateName.value,
        skills: skills.value,
        credibilityScore: credibilityScore.value
      }))
    } catch { /* localStorage 不可用时静默失败 */ }
  }

  function setResume(id, name, skillList, score = null) {
    resumeId.value = id
    candidateName.value = name || ''
    skills.value = skillList || []
    credibilityScore.value = score
    _persist()
  }

  function clear() {
    resumeId.value = ''
    candidateName.value = ''
    skills.value = []
    credibilityScore.value = null
    try { localStorage.removeItem(STORAGE_KEY) } catch {}
  }

  return { resumeId, candidateName, skills, credibilityScore, setResume, clear }
})
