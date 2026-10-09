import { API_BASE_URL } from '../../api/client.js'
const SESSION_KEY = 'careernova-skill-session'
let sessionPromise

async function request(path, options = {}) {
  let response
  try { response = await fetch(`${API_BASE_URL}/api/component01/skills${path}`, options) }
  catch { throw new Error('Cannot reach the assessment service. Check that the backend is running.') }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : 'The assessment request failed.'
    const error = new Error(detail)
    error.status = response.status
    throw error
  }
  return data
}

export function savedSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null') }
  catch { return null }
}

async function session() {
  const current = savedSession()
  if (current?.access_token && current?.candidate_id) return current
  if (!sessionPromise) sessionPromise = request('/session', { method: 'POST' }).then(value => {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(value))
    return value
  }).finally(() => { sessionPromise = null })
  return sessionPromise
}

export async function uploadCV(file) {
  const current = await session()
  const body = new FormData()
  body.append('candidate_id', current.candidate_id)
  body.append('file', file)
  try {
    return await request('/upload', { method: 'POST', headers: { Authorization: `Bearer ${current.access_token}` }, body })
  } catch (error) {
    if (error.status === 401) sessionStorage.removeItem(SESSION_KEY)
    throw error
  }
}

export async function getSkillDetails() {
  const current = savedSession()
  if (!current) return null
  try { return await request(`/${encodeURIComponent(current.candidate_id)}/details`, { headers: { Authorization: `Bearer ${current.access_token}` } }) }
  catch (error) {
    if (error.status === 404) return null
    if (error.status === 401) sessionStorage.removeItem(SESSION_KEY)
    throw error
  }
}
