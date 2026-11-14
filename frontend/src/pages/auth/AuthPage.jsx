// Sign-in / register / forgot / reset card. The auth logic (validation, requests, redirects,
// messages) is unchanged; only the presentation is new. Rendered inside AuthLayout.
import { useEffect, useRef, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { AnimatePresence, m, useReducedMotion } from 'motion/react'
import Icon from '../../components/Icon.jsx'
import { useAuth } from '../../auth/AuthContext.jsx'
import { authRequest } from '../../auth/authApi.js'
import { EASE } from '../home/motion.js'
import { Checkbox, PasswordField, TextField } from './authFields.jsx'

const content = {
  login: ['Welcome back.', 'Your next chapter is waiting. Sign in to your workspace.', 'Log in'],
  register: ['Start your journey.', 'Create your account and take the first step toward your future.', 'Create account'],
  forgot: ['Forgot your password?', 'Enter your email and we’ll send you a link to reset it.', 'Send reset link'],
  reset: ['A fresh start.', 'Choose a new password to get back to your workspace.', 'Update password'],
}
const EMAIL = /^[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+$/
const REMEMBERED_KEY = 'careernova-remembered-name' // first name only, kept when "Remember me" is ticked

const card = {
  hidden: { opacity: 0, x: 24 },
  show: { opacity: 1, x: 0, scale: 1, transition: { duration: 0.55, ease: EASE, staggerChildren: 0.055, delayChildren: 0.08 } },
  leave: { opacity: 0, scale: 0.96, transition: { duration: 0.35, ease: EASE } },
}
const item = { hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE } } }
const wait = ms => new Promise(resolve => setTimeout(resolve, ms))

function rememberedName() {
  try { return localStorage.getItem(REMEMBERED_KEY) || '' } catch { return '' }
}

function GoogleIcon() {
  return <svg className="af-google-icon" width="19" height="19" viewBox="0 0 24 24" aria-hidden="true"><path fill="#4285F4" d="M21.6 12.23c0-.71-.06-1.39-.18-2.05H12v3.88h5.38a4.6 4.6 0 0 1-2 3.02v2.51h3.24c1.89-1.74 2.98-4.3 2.98-7.36Z"/><path fill="#34A853" d="M12 22c2.7 0 4.96-.9 6.62-2.41l-3.24-2.51c-.9.6-2.04.97-3.38.97-2.6 0-4.8-1.76-5.59-4.12H3.07v2.59A10 10 0 0 0 12 22Z"/><path fill="#FBBC05" d="M6.41 13.93A6 6 0 0 1 6.1 12c0-.67.11-1.32.31-1.93V7.48H3.07A10 10 0 0 0 2 12c0 1.61.38 3.14 1.07 4.52l3.34-2.59Z"/><path fill="#EA4335" d="M12 5.95c1.47 0 2.79.51 3.83 1.51L18.7 4.6A9.6 9.6 0 0 0 12 2a10 10 0 0 0-8.93 5.48l3.34 2.59C7.2 7.71 9.4 5.95 12 5.95Z"/></svg>
}

export default function AuthPage({ mode = 'login' }) {
  const { user, loading, login, loginWithGoogle, refresh } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const reduced = useReducedMotion()
  const cardRef = useRef(null)
  const signingIn = useRef(false) // keeps this page up for the success animation after login
  const [values, setValues] = useState({ full_name: '', email: location.state?.email || '', password: '', confirm: '', remember_me: false })
  const [errors, setErrors] = useState({})
  const [error, setError] = useState('')
  const [message, setMessage] = useState(location.state?.message || '')
  const [busy, setBusy] = useState(false)
  const [googleBusy, setGoogleBusy] = useState(false)
  const [phase, setPhase] = useState('idle') // idle | success | leaving (login only)
  const [googleSpin, setGoogleSpin] = useState(0)
  const [returning] = useState(() => mode === 'login' ? rememberedName() : '')
  const [, subtitle, action] = content[mode]
  const title = mode === 'login' && returning ? `Welcome back, ${returning}.` : content[mode][0]
  const token = new URLSearchParams(location.hash.slice(1)).get('token') || ''
  const emailValid = EMAIL.test(values.email.trim())

  const update = event => {
    const { name, value, type, checked } = event.target
    setValues(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
    setErrors(prev => ({ ...prev, [name]: '' }))
    setError('')
  }

  // A gentle shake when something goes wrong (transform only; skipped for reduced motion).
  function shake() {
    if (reduced || !cardRef.current?.animate) return
    cardRef.current.animate([{ transform: 'translateX(0)' }, { transform: 'translateX(-8px)' }, { transform: 'translateX(6px)' }, { transform: 'translateX(-4px)' }, { transform: 'translateX(0)' }], { duration: 420, easing: 'ease-out' })
  }

  // After a successful login, remember the first name for next time only if asked to.
  useEffect(() => {
    if (phase !== 'success' || !user) return
    try {
      if (values.remember_me) localStorage.setItem(REMEMBERED_KEY, user.full_name.split(/\s+/)[0])
      else localStorage.removeItem(REMEMBERED_KEY)
    } catch { /* storage unavailable */ }
  }, [phase, user, values.remember_me])

  async function submit(event) {
    event.preventDefault()
    if (busy || phase !== 'idle') return
    const next = {}
    if (mode === 'register' && values.full_name.trim().length < 2) next.full_name = 'Please enter your full name.'
    if (mode !== 'reset' && !EMAIL.test(values.email.trim())) next.email = 'Enter a valid email address.'
    if (mode !== 'forgot') {
      if (!values.password) next.password = 'Enter your password.'
      else if (mode !== 'login' && values.password.length < 12) next.password = 'Use at least 12 characters.'
    }
    if (['register', 'reset'].includes(mode) && values.password !== values.confirm) next.confirm = 'Passwords do not match.'
    setErrors(next)
    if (Object.keys(next).length) { shake(); return }
    setBusy(true); setError(''); setMessage('')
    try {
      if (mode === 'login') {
        signingIn.current = true
        await login({ email: values.email.trim(), password: values.password, remember_me: values.remember_me })
        // Button shows a tick, the card scales away, then Home opens.
        setPhase('success')
        await wait(reduced ? 150 : 650)
        setPhase('leaving')
        await wait(reduced ? 100 : 330)
        navigate('/', { replace: true })
      } else if (mode === 'register') {
        await authRequest('/register', { full_name: values.full_name.trim(), email: values.email.trim(), password: values.password })
        navigate('/login', { replace: true, state: { email: values.email.trim(), message: 'Your account is ready. Log in to begin.' } })
      } else if (mode === 'forgot') {
        const result = await authRequest('/forgot-password', { email: values.email.trim() })
        setMessage(result.message)
      } else {
        if (!token) throw new Error('This reset link is incomplete. Request a new one.')
        const result = await authRequest('/reset-password', { token, password: values.password })
        await refresh()
        navigate('/login', { replace: true, state: { message: result.message } })
      }
    } catch (err) { signingIn.current = false; setError(err.message); setPhase('idle'); shake() }
    finally { setBusy(false) }
  }

  async function googleLogin() {
    setGoogleSpin(n => n + 1)
    setGoogleBusy(true); setError(''); setMessage('')
    try { await loginWithGoogle() }
    catch (err) { setError(err.message || 'Google sign-in is unavailable. Please try again.'); setGoogleBusy(false); shake() }
  }

  if (loading) return <div className="af-status" role="status"><span className="af-status-spinner" aria-hidden="true" />Opening CareerNova…</div>
  if (user && mode !== 'reset' && !signingIn.current) return <Navigate to="/" replace />

  const state = phase !== 'idle' ? 'success' : busy ? 'busy' : 'idle'
  return <m.div ref={cardRef} className="af-card" variants={card} initial="hidden" animate={phase === 'leaving' ? 'leave' : 'show'}>
    <m.span className="af-symbol" variants={item}><Icon size={25} /></m.span>
    <m.p className="af-eyebrow" variants={item}>YOUR CAREER STARTS HERE</m.p>
    <m.h2 variants={item}>{title}</m.h2>
    <m.p className="af-subtitle" variants={item}>{subtitle}</m.p>
    {['login', 'register'].includes(mode) && <>
      <m.div variants={item}>
        <button type="button" className={`af-google ${googleBusy ? 'is-busy' : ''}`} onClick={googleLogin} disabled={busy || googleBusy || phase !== 'idle'}>
          {googleBusy ? <span className="af-spinner af-spinner-dark" aria-hidden="true" /> : <span key={googleSpin} className={googleSpin ? 'af-google-spin' : ''}><GoogleIcon /></span>}
          {googleBusy ? 'Connecting to Google…' : 'Continue with Google'}
        </button>
      </m.div>
      <m.div className="af-divider" variants={item}><span>or continue with email</span></m.div>
    </>}
    <form onSubmit={submit} noValidate>
      <AnimatePresence initial={false}>
        {message && <m.div key="message" className="af-success" role="status" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}><Icon name="check" size={18} />{message}</m.div>}
        {error && <m.div key="error" className="af-error" role="alert" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, transition: { duration: 0.15 } }}><Icon name="alert" size={17} />{error}</m.div>}
      </AnimatePresence>
      <fieldset disabled={busy || googleBusy || phase !== 'idle'}>
        {mode === 'register' && <m.div variants={item}><TextField name="full_name" label="Full name" icon="user" autoComplete="name" maxLength={100} value={values.full_name} onChange={update} required error={errors.full_name} valid={values.full_name.trim().length >= 2} /></m.div>}
        {mode !== 'reset' && <m.div variants={item}><TextField name="email" label="Email address" icon="mail" type="email" autoComplete="email" maxLength={254} value={values.email} onChange={update} required error={errors.email} valid={emailValid} /></m.div>}
        {mode !== 'forgot' && <m.div variants={item}><PasswordField name="password" label="Password" value={values.password} onChange={update} error={errors.password} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
          {mode !== 'login' && <p className="af-hint">Use at least 12 characters. A memorable passphrase works well.</p>}</m.div>}
        {['register', 'reset'].includes(mode) && <m.div variants={item}><PasswordField name="confirm" label="Confirm password" value={values.confirm} onChange={update} error={errors.confirm} autoComplete="new-password" /></m.div>}
        {mode === 'login' && <m.div className="af-options" variants={item}>
          <Checkbox name="remember_me" checked={values.remember_me} onChange={update}>Remember me</Checkbox>
          <Link to="/forgot-password">Forgot password?</Link>
        </m.div>}
        <m.div variants={item}>
          <button className={`af-submit is-${state}`} type="submit" disabled={busy || phase !== 'idle'}>
            <span className="af-submit-bg" aria-hidden="true" />
            <AnimatePresence mode="wait" initial={false}>
              {state === 'idle' && <m.span key="idle" className="af-submit-label" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.1 } }}>{action}<span className="af-submit-arrow" aria-hidden="true"><Icon name="arrow" size={18} /></span></m.span>}
              {state === 'busy' && <m.span key="busy" className="af-submit-label" initial={{ opacity: 0, scale: 0.6 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}><span className="af-spinner" aria-hidden="true" /><span className="sr-only">Please wait…</span></m.span>}
              {state === 'success' && <m.span key="done" className="af-submit-label" initial={{ opacity: 0, scale: 0.6 }} animate={{ opacity: 1, scale: 1 }}>
                <svg className="af-submit-check" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5" pathLength="1" /></svg>
                <span className="sr-only">Signed in</span></m.span>}
            </AnimatePresence>
          </button>
        </m.div>
      </fieldset>
    </form>
    <m.p className="af-switch" variants={item}>{mode === 'login' ? <>Don’t have an account? <Link to="/register">Register now</Link></> : mode === 'register' ? <>Already have an account? <Link to="/login">Log in</Link></> : <Link to="/login">Back to login</Link>}</m.p>
    <m.div className="af-reassurance" variants={item}><svg className="af-shield" width="15" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M12 2 3 6v6c0 6 9 10 9 10s9-4 9-10V6l-9-4Z" /><path d="m8 12 3 3 5-6" /></svg> Your next step, in a secure workspace.</m.div>
  </m.div>
}
