// Owner: Dewmi - Component 04: Career Readiness Assessment form API helpers.
// Reads Component 01 (CV skills) through its existing helper. The target career is decided by the backend from
// Component 03's recommendation for the signed-in CV candidate; the browser never sends a chosen career.
import { API_BASE_URL } from '../../api/client.js'
import { getSkillDetails, savedSession } from '../component01/skillApi.js'
import { candidateKey, reuse } from '../../api/resourceCache.js'

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

// The career recommended by Component 03 (rank, score, C03's top 5, fallback). Errors carry .status:
// 401 not signed in, 409 no CV assessment yet, 422 no supported career, 503/504 Component 03 unavailable.
export function getRecommendedCareer() {
  return request('/recommended-career', { headers: authHeaders() })
}

// Skills to rate for the Component 03 career, decided on the server. expectedCareerId is the career the server
// itself returned from /recommended-career (never a student choice): if Component 03's result changed in the
// meantime the server answers 409 instead of silently switching career.
export function getQuestions(c1Skills, expectedCareerId) {
  return request('/questions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ c1_skills: c1Skills, ...(expectedCareerId ? { career_id: expectedCareerId } : {}) }),
  })
}

// Has Component 03's recommended career changed since this assessment? Never changes the assessment.
export function getCareerCheck(assessmentId) {
  return request(`/${encodeURIComponent(assessmentId)}/career-check`, { headers: authHeaders() })
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

// Optional proof for a claimed skill; stored as "pending" until a new CV assessment confirms it.
// Sent as multipart/form-data; the response includes the regenerated roadmap in "analysis".
export function submitEvidence(skillId, type, url, { file, description } = {}) {
  const body = new FormData()
  body.append('candidate_id', savedSession()?.candidate_id || '')
  body.append('skill_id', skillId)
  body.append('proof_type', type)
  if (url) body.append('url', url)
  if (file) body.append('file', file)
  if (description) body.append('description', description)
  return request('/evidence', { method: 'POST', headers: authHeaders(), body }, ROOT)
}

export function listEvidence() {
  const candidateId = savedSession()?.candidate_id
  return candidateId ? request(`/evidence/${encodeURIComponent(candidateId)}`, { headers: authHeaders() }, ROOT) : Promise.resolve([])
}

// "Check again": re-runs the link checks (e.g. GitHub was unreachable); returns the evidence + regenerated "analysis".
export function recheckEvidence(evidenceId) {
  return request(`/evidence/${encodeURIComponent(evidenceId)}/recheck`, { method: 'POST', headers: authHeaders() }, ROOT)
}

export function deleteEvidence(evidenceId) {
  return request(`/evidence/${encodeURIComponent(evidenceId)}`, { method: 'DELETE', headers: authHeaders() }, ROOT)
}

export function hasCvSession() {
  return Boolean(savedSession()?.access_token)
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
    const details = await reuse(candidateKey('c01:details'), getSkillDetails) // already loaded by Component 01
    return (details?.skills || []).map(skill => ({ name: skill.name, level: skill.level }))
  } catch {
    return []
  }
}

// ---- Adaptive learning tutor (needs the CV session: progress is private to the student) ----
const LEARN = id => `/learning/${encodeURIComponent(id)}`

export function getLearningPlan(assessmentId) {
  return request(LEARN(assessmentId), { headers: authHeaders() }, ROOT)
}

// kind "lesson" (topicId required, optional mode) or "diagnostic" (optional scope "test_out" + topicId).
// Questions arrive without answers; answers and explanations come back only after an attempt.
export function openActivity(assessmentId, { skillId, topicId, kind = 'lesson', mode, scope }) {
  const params = new URLSearchParams({ skill_id: skillId, kind })
  if (topicId) params.set('topic_id', topicId)
  if (mode) params.set('mode', mode)
  if (scope) params.set('scope', scope)
  return request(`${LEARN(assessmentId)}/activity?${params}`, { headers: authHeaders() }, ROOT)
}

// Returns graded feedback, the adaptive decision, the next activity, the new plan and the regenerated "analysis".
export function submitLearningAttempt(assessmentId, body) {
  return request(`${LEARN(assessmentId)}/attempts`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() }, body: JSON.stringify(body),
  }, ROOT)
}

export function getLearningHistory(assessmentId) {
  return request(`${LEARN(assessmentId)}/history`, { headers: authHeaders() }, ROOT)
}

export function generateLessons(assessmentId, skillId) {
  return request(`${LEARN(assessmentId)}/generate/${encodeURIComponent(skillId)}`, { method: 'POST', headers: authHeaders() }, ROOT)
}
