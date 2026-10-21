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

// IPIP-50 Big Five questionnaire: statements in display order (attention checks included).
export function getQuestionnaire() {
  return request('/questionnaire')
}

// Questionnaire answers {itemId: 1..5} -> normalised trait levels (0-1) and validity warnings.
export function scoreQuestionnaire(responses) {
  return request('/questionnaire/score', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ responses }),
  })
}

// Situational judgement scenarios (the scoring key stays on the server).
export function getScenarios() {
  return request('/sjt')
}

// Chosen options {scenarioId: optionId} -> trait tendencies (0-1).
export function scoreScenarios(responses) {
  return request('/sjt/score', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ responses }),
  })
}

// All completed parts -> fused profile + Personality Consistency Score (versioned JSON for Component 3).
export function assessProfile({ questionnaire, sjt, answers }) {
  return request('/assess', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ questionnaire, sjt, answers }),
  })
}

// Behavioural text model: free-text answers -> P(high trait) for each Big Five trait.
export function analyseTextAnswers(answers) {
  return request('/text-traits', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers }),
  })
}


//backend 
//frontend 
