import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { authRequest } from './authApi.js'

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
  const acceptSession = useCallback(value => {
    if (sessionStorage.getItem('careernova-account-owner') !== value.user.id) clearCandidate()
    sessionStorage.setItem('careernova-account-owner', value.user.id)
    setSession(value)
    setError('')
  }, [])
  const refresh = useCallback(async () => {
    const version = sessionVersion.current
    try {
      const value = await authRequest('/me')
      if (version === sessionVersion.current) acceptSession(value)
    }
    catch (err) {
      if (version !== sessionVersion.current) return
      if (err.status === 401) { clearCandidate(); setSession(null); setError('') }
      else setError(err.message)
    } finally { setLoading(false) }
  }, [acceptSession])
  useEffect(() => {
    refresh()
    const sync = event => { if (event.key === 'careernova-auth-event') refresh() }
    window.addEventListener('focus', refresh)
    window.addEventListener('storage', sync)
    return () => { window.removeEventListener('focus', refresh); window.removeEventListener('storage', sync) }
  }, [refresh])
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
    acceptSession(value)
    announce()
  }
  async function logout() {
    await authRequest('/logout', {})
    sessionVersion.current += 1
    clearCandidate()
    setSession(null)
    announce()
  }
  return <AuthContext.Provider value={{ user: session?.user, loading, error, refresh, login, logout }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)

export function RequireAuth({ children }) {
  const { user, loading, error, refresh } = useAuth()
  if (loading) return <div className="auth-status" role="status">Opening your workspace…</div>
  if (error) return <div className="auth-status"><p role="alert">{error}</p><button onClick={refresh}>Try again</button></div>
  return user ? children : <Navigate to="/login" replace />
}
