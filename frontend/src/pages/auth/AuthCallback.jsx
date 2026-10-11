import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext.jsx'
import { finishGoogleSignIn } from '../../auth/supabaseClient.js'
import Icon from '../../components/Icon.jsx'

export default function AuthCallback() {
  const [error, setError] = useState('')
  const { refresh } = useAuth()
  const navigate = useNavigate()
  useEffect(() => {
    let active = true
    async function complete() {
      try {
        await finishGoogleSignIn(window.location.href)
        if (!active) return
        await refresh()
        if (active) navigate('/', { replace: true })
      } catch (err) {
        if (active) {
          setError(err.message || 'Google sign-in failed. Please try again.')
          // Remove single-use codes and provider error details from browser history.
          window.history.replaceState(window.history.state, '', '/auth/callback')
        }
      }
    }
    complete()
    return () => { active = false }
  }, [navigate, refresh])
  return <main className="auth-status"><div className="auth-callback-card">
    <span className="auth-form-symbol"><Icon size={25} /></span>
    <h1>{error ? 'Let’s try that again.' : 'Welcome to CareerNova.'}</h1>
    {error ? <><p role="alert" className="auth-error">{error}</p><Link className="button" to="/login" replace>Back to login</Link></>
      : <p role="status">Completing your Google sign-in…</p>}
  </div></main>
}
