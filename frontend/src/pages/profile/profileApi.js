// Profile API (backend/app/auth/profile.py). Email/password accounts use the session cookie;
// Google accounts send their Supabase access token, which the backend confirms with Supabase.
import { API_BASE_URL } from '../../api/client.js'
import { supabase } from '../../auth/supabaseClient.js'

const PROVIDER_KEY = 'careernova-auth-provider' // written by AuthContext

export function signInProvider() {
  try { return localStorage.getItem(PROVIDER_KEY) === 'google' ? 'google' : 'password' }
  catch { return 'password' }
}

async function authHeaders() {
  if (signInProvider() !== 'google' || !supabase) return {}
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ? { Authorization: `Bearer ${data.session.access_token}` } : {}
}

async function request(path, { method = 'GET', json, form, raw = false } = {}) {
  const headers = await authHeaders()
  if (json !== undefined) headers['Content-Type'] = 'application/json'
  let response
  try {
    response = await fetch(`${API_BASE_URL}/api/auth${path}`, {
      method, credentials: 'include', headers,
      body: json !== undefined ? JSON.stringify(json) : form,
    })
  } catch {
    throw new Error('Unable to reach the account service. Check your connection and try again.')
  }
  if (response.ok && raw) return response
  const data = response.status === 204 ? null : await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = data?.detail
    const fields = {}
    if (Array.isArray(detail)) for (const item of detail) {
      const field = item.loc?.[item.loc.length - 1]
      if (typeof field === 'string') fields[field] = String(item.msg || '').replace(/^Value error, /, '')
    }
    const error = new Error(typeof detail === 'string' ? detail
      : Object.keys(fields).length ? 'Some details need fixing before they can be saved.'
        : response.status === 404 ? 'The profile service is not available on this backend yet. Restart the backend so it loads the new profile routes.'
          : 'The account service is unavailable. Please try again.')
    error.status = response.status
    error.fields = fields
    throw error
  }
  return data
}

export const getProfile = () => request('/profile')
export const saveProfile = body => request('/profile', { method: 'PUT', json: body })
export const saveConsent = researchUse => request('/profile/consent', { method: 'PUT', json: { research_use: researchUse } })
export const exportProfile = () => request('/profile/export')
export const changePassword = (current, next) => request('/password', { method: 'POST', json: { current_password: current, new_password: next } })
export const deleteAccount = () => request('/profile/delete', { method: 'POST', json: { confirm: 'DELETE' } })
export const deletePhoto = () => request('/profile/avatar', { method: 'DELETE' })

export function uploadPhoto(file) {
  const form = new FormData()
  form.append('file', file)
  return request('/profile/avatar', { method: 'PUT', form })
}

// The photo needs credentials, so it is fetched and shown through an object URL.
export async function photoUrl() {
  const response = await request('/profile/avatar', { raw: true })
  return URL.createObjectURL(await response.blob())
}

// Called after a CV upload on Home. Only the file name and time are kept, never the file.
export function recordCvUpload(fileName) {
  return request('/profile/cv', { method: 'PUT', json: { file_name: fileName } })
}
