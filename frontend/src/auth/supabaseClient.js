import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL?.trim()
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY?.trim()

// Only the project's public anon key belongs in a Vite environment variable.
// The callback route owns the PKCE exchange, so automatic URL detection is off.
export const supabase = url && anonKey ? createClient(url, anonKey, {
  auth: { persistSession: true, autoRefreshToken: true, flowType: 'pkce', detectSessionInUrl: false },
}) : null

export function requireSupabase() {
  if (!supabase) throw new Error('Google sign-in is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY, then restart or redeploy the frontend.')
  return supabase
}

export function googleSession(session) {
  const metadata = session.user.user_metadata || {}
  const avatar = metadata.avatar_url || metadata.picture || ''
  return {
    provider: 'google', expires_at: session.expires_at,
    user: {
      id: session.user.id, email: session.user.email || '',
      full_name: metadata.full_name || metadata.name || session.user.email?.split('@')[0] || 'CareerNova member',
      avatar_url: /^https:\/\//i.test(avatar) ? avatar : '',
    },
  }
}

export async function startGoogleSignIn() {
  const client = requireSupabase()
  const { error } = await client.auth.signInWithOAuth({
    provider: 'google', options: { redirectTo: window.location.origin + '/auth/callback' },
  })
  if (error) throw error
}

let callbackCode
let callbackPromise

export async function finishGoogleSignIn(url) {
  const client = requireSupabase()
  const callback = new URL(url)
  const fragment = new URLSearchParams(callback.hash.slice(1))
  const oauthError = callback.searchParams.get('error_description') || fragment.get('error_description')
    || callback.searchParams.get('error') || fragment.get('error')
  if (oauthError) throw new Error(`Google sign-in was not completed: ${oauthError}`)
  const code = callback.searchParams.get('code')
  if (code) {
    // OAuth codes are single-use. React StrictMode may mount this route twice.
    if (callbackCode !== code || !callbackPromise) {
      callbackCode = code
      const flowId = callback.searchParams.get('sb_flow_id')
      callbackPromise = client.auth.exchangeCodeForSession(code, flowId ? { flowId } : undefined)
    }
    const { error } = await callbackPromise
    if (error) throw new Error(`Google sign-in could not be completed. Please try again. ${error.message}`)
  }
  const { data, error } = await client.auth.getSession()
  if (error) throw error
  if (!data.session) throw new Error('No Google session was found. Return to login and try again in the same browser.')
  return data.session
}
