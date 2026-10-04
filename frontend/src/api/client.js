// SHARED FILE - controlled by the group leader.
// Lightweight API helpers built on the native fetch API.

export const API_BASE_URL = 'http://127.0.0.1:8000'

async function handleResponse(response) {
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`API error ${response.status}: ${text}`)
  }
  return response.json()
}

export async function apiGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`)
  return handleResponse(response)
}

export async function apiPost(path, data) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  return handleResponse(response)
}
