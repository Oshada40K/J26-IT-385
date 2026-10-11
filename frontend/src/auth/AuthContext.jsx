import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { authRequest } from './authApi.js'
import { googleSession, startGoogleSignIn, supabase } from './supabaseClient.js'

const PROVIDER_KEY = 'careernova-auth-provider'

const AuthContext = createContext(null)

function clearCandidate() {
  sessionStorage.removeItem('careernova-skill-session')
  sessionStorage.removeItem('careernova-account-owner')
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const sessionVersion = useRef(0)
  const provider = useRef(null)
  const acceptSession = useCallback(value => {
    const owner = `${value.provider}:${value.user.id}`
    if (sessionStorage.getItem('careernova-account-owner') !== owner) clearCandidate()
    sessionStorage.setItem('careernova-account-owner', owner)
    provider.current = value.provider
    localStorage.setItem(PROVIDER_KEY, value.provider)
    setSession(value)
    setError('')
  }, [])
  const refresh = useCallback(async () => {
    const version = sessionVersion.current
    try {
      if (supabase) {
        const { data, error: sessionError } = await supabase.auth.getSession()
        if (sessionError) throw sessionError
        if (data.session) {
          const { error: userError } = await supabase.auth.getUser()
          if (userError) throw userError
          if (version === sessionVersion.current) acceptSession(googleSession(data.session))
          return
        }
      }
      // A Google logout must not restore an older email/password cookie.
      if (['google', 'signed-out'].includes(localStorage.getItem(PROVIDER_KEY))) {
        if (version === sessionVersion.current) { clearCandidate(); setSession(null); setError(''); provider.current = null }
        return
      }
      const value = await authRequest('/me')
      if (version === sessionVersion.current) acceptSession({ ...value, provider: 'password' })
    }
    catch (err) {
      if (version !== sessionVersion.current) return
      if ([401, 403, 404].includes(err.status)) { clearCandidate(); setSession(null); setError(''); provider.current = null }
      else if (provider.current) setError(err.message)
      // A missing legacy backend must not prevent a new Google login.
      else { setSession(null); setError('') }
    } finally { setLoading(false) }
  }, [acceptSession])
  useEffect(() => {
    const subscription = supabase?.auth.onAuthStateChange((event, value) => {
      if (event === 'INITIAL_SESSION') return // refresh() validates the initial session.
      if (value) {
        sessionVersion.current += 1
        acceptSession(googleSession(value))
        setLoading(false)
      } else if (event === 'SIGNED_OUT' && provider.current === 'google') {
        sessionVersion.current += 1
        localStorage.setItem(PROVIDER_KEY, 'signed-out')
        provider.current = null
        clearCandidate(); setSession(null); setError(''); setLoading(false)
      }
    }).data.subscription
    refresh()
    const sync = event => { if (event.key === 'careernova-auth-event' || event.key === PROVIDER_KEY) refresh() }
    window.addEventListener('focus', refresh)
    window.addEventListener('storage', sync)
    return () => { subscription?.unsubscribe(); window.removeEventListener('focus', refresh); window.removeEventListener('storage', sync) }
  }, [refresh, acceptSession])
  useEffect(() => {
    if (!session) return
    // Refresh periodically as well as at expiry; avoids long setTimeout overflow.
    const delay = Math.min(60_000, Math.max(0, session.expires_at * 1000 - Date.now()))
    const timer = setTimeout(refresh, delay)
    return () => clearTimeout(timer)
  }, [session, refresh])
  const announce = () => localStorage.setItem('careernova-auth-event', `${Date.now()}-${Math.random()}`)
  async function login(data) {
    await authRequest('/login', data)
    // Confirm the browser accepted the cookie before granting dashboard access.
    const value = await authRequest('/me')
    sessionVersion.current += 1
    acceptSession({ ...value, provider: 'password' })
    announce()
  }
  async function logout() {
    if (provider.current === 'google') {
      const { error: signOutError } = await supabase.auth.signOut({ scope: 'local' })
      if (signOutError) throw signOutError
    } else await authRequest('/logout', {})
    sessionVersion.current += 1
    localStorage.setItem(PROVIDER_KEY, 'signed-out')
    provider.current = null
    clearCandidate()
    setSession(null)
    announce()
  }
  async function loginWithGoogle() {
    // Set before leaving the page so the OAuth callback never needs the legacy API.
    localStorage.setItem(PROVIDER_KEY, 'google')
    await startGoogleSignIn()
  }
  return <AuthContext.Provider value={{ user: session?.user, loading, error, refresh, login, loginWithGoogle, logout }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)

export function RequireAuth({ children }) {
  const { user, loading, error, refresh } = useAuth()
  if (loading) return <div className="auth-status" role="status">Opening your workspace…</div>
  if (error) return <div className="auth-status"><p role="alert">{error}</p><button onClick={refresh}>Try again</button></div>
  return user ? children : <Navigate to="/login" replace />
}
