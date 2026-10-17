import { API_BASE_URL } from '../../api/client.js'

async function request(path, options = {}) {
  let response
  try { response = await fetch(`${API_BASE_URL}/api/personality${path}`, options) }
  catch { throw new Error('Cannot reach the personality service. Check that the backend is running.') }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : 'The personality analysis request failed.'
    const error = new Error(detail)
    error.status = response.status
    throw error
  }
  return data
}

// Behavioural text model: free-text answers -> P(high trait) for each Big Five trait.
export function analyseTextAnswers(answers) {
  return request('/text-traits', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers }),
  })
}
