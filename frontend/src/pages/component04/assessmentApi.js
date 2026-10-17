// Owner: Dewmi - Component 04: Career Readiness Assessment form API helpers.
// Reads Component 01 (CV skills) and Component 03 (top careers) through their existing helpers.
import { API_BASE_URL } from '../../api/client.js'
import { getSkillDetails, savedSession } from '../component01/skillApi.js'
import { getCareerResult } from '../component03/careerApi.js'

const BASE = `${API_BASE_URL}/api/roadmap/assessment`

function readableDetail(detail) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map(item => String(item.msg || '').replace(/^Value error, /, '')).filter(Boolean).join(' ')
  }
  return ''
}

async function request(path, options = {}) {
  let response
  try { response = await fetch(`${BASE}${path}`, options) }
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

export function submitAssessment(payload) {
  const session = savedSession()
  const headers = { 'Content-Type': 'application/json' }
  if (session?.access_token) headers.Authorization = `Bearer ${session.access_token}`
  return request('', {
    method: 'POST',
    headers,
    body: JSON.stringify({ ...payload, candidate_id: session?.candidate_id || null }),
  })
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
