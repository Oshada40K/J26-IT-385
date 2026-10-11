import { API_BASE_URL } from '../api/client.js'

export async function authRequest(path, data) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}/api/auth${path}`, {
      method: data === undefined ? 'GET' : 'POST',
      credentials: 'include',
      headers: data === undefined ? {} : { 'Content-Type': 'application/json' },
      body: data === undefined ? undefined : JSON.stringify(data),
    })
  } catch {
    throw new Error('Unable to reach the account service. Check your connection and try again.')
  }
  const result = response.status === 204 ? null : await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = result?.detail
    const error = new Error(typeof detail === 'string' ? detail
      : Array.isArray(detail) ? detail.map(item => item.msg.replace(/^Value error, /, '')).join(' ')
        : 'The account service is unavailable. Please try again.')
    error.status = response.status
    throw error
  }
  return result
}
