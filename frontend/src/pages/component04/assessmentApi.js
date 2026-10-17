// Owner: Dewmi - Component 04: Career Readiness Assessment form API helpers.
// Reads Component 01 (CV skills) and Component 03 (top careers) through their existing helpers.
import { API_BASE_URL } from '../../api/client.js'
import { getSkillDetails, savedSession } from '../component01/skillApi.js'
import { getCareerResult } from '../component03/careerApi.js'

const ROOT = `${API_BASE_URL}/api/roadmap`
const BASE = `${ROOT}/assessment`
const LAST_KEY = 'careernova-c4-assessment'

function authHeaders() {
  const session = savedSession()
  return session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}
}

function readableDetail(detail) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map(item => String(item.msg || '').replace(/^Value error, /, '')).filter(Boolean).join(' ')
  }
  return ''
}

async function request(path, options = {}, base = BASE) {
  let response
  try { response = await fetch(`${base}${path}`, options) }
  catch { throw new Error('Cannot reach the assessment service. Check that the backend is running.') }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(readableDetail(data.detail) || 'The assessment request failed. Please try again.')
    error.status = response.status
    throw error
  }
  return data
}

export function getCareers() {
  return request('/careers')
}

export function getQuestions(careerId, c1Skills) {
  return request('/questions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ career_id: careerId, c1_skills: c1Skills }),
  })
}

export async function submitAssessment(payload) {
  const session = savedSession()
  const saved = await request('', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ ...payload, candidate_id: session?.candidate_id || null }),
  })
  try { sessionStorage.setItem(LAST_KEY, saved.assessment_id) } catch { /* storage unavailable */ }
  return saved
}

export function getAssessment(assessmentId) {
  return request(`/${encodeURIComponent(assessmentId)}`, { headers: authHeaders() })
}

export function getAnalysis(assessmentId) {
  return request(`/analysis/${encodeURIComponent(assessmentId)}`, { headers: authHeaders() }, ROOT)
}

// The candidate's latest saved assessment, or the last one submitted in this browser session.
export async function findLatestAssessment() {
  if (savedSession()?.access_token) {
    try {
      const latest = await request('/latest', { headers: authHeaders() })
      if (latest) return latest
    } catch (error) { if (error.status !== 401) throw error }
  }
  let lastId = null
  try { lastId = sessionStorage.getItem(LAST_KEY) } catch { /* storage unavailable */ }
  if (!lastId) return null
  try { return await getAssessment(lastId) }
  catch { return null }
}

// C1 skills from the uploaded CV; an empty list when no CV has been assessed yet.
export async function loadCvSkills() {
  try {
    const details = await getSkillDetails()
    return (details?.skills || []).map(skill => ({ name: skill.name, level: skill.level }))
  } catch {
    return []
  }
}

// C3's ranked careers for the current candidate (or the sample profile).
export async function loadCareerMatches() {
  try {
    const data = await getCareerResult('topJobs', API_BASE_URL, savedSession())
    return data.jobs || []
  } catch {
    return []
  }
}
