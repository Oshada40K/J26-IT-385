import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import Icon from '../../components/Icon.jsx'
import { useAuth } from '../../auth/AuthContext.jsx'
import { authRequest } from '../../auth/authApi.js'
import './auth.css'

const content = {
  login: ['Welcome back.', 'Your next chapter is waiting. Sign in to your workspace.', 'Log in'],
  register: ['Start your journey.', 'Create your account and take the first step toward your future.', 'Create account'],
  forgot: ['Forgot your password?', 'Enter your email and we’ll send you a link to reset it.', 'Send reset link'],
  reset: ['A fresh start.', 'Choose a new password to get back to your workspace.', 'Update password'],
}

function PasswordField({ name, label, value, onChange, error, autoComplete }) {
  const [visible, setVisible] = useState(false)
  return <div className="auth-field"><label htmlFor={name}>{label}</label><div className="auth-password">
    <input id={name} name={name} type={visible ? 'text' : 'password'} value={value} onChange={onChange}
      autoComplete={autoComplete} maxLength={128} required aria-invalid={!!error}
      aria-describedby={error ? `${name}-error` : undefined} placeholder={name === 'confirm' ? 'Re-enter your password' : 'Enter your password'} />
    <button type="button" className="auth-show" aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`} aria-pressed={visible} onClick={() => setVisible(v => !v)}>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" />{visible && <path d="m3 3 18 18" />}</svg>
    </button></div>{error && <span className="auth-field-error" id={`${name}-error`}>{error}</span>}</div>
}

export default function AuthPage({ mode = 'login' }) {
  const { user, loading, login, loginWithGoogle, refresh } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [values, setValues] = useState({ full_name: '', email: location.state?.email || '', password: '', confirm: '', remember_me: false })
  const [errors, setErrors] = useState({})
  const [error, setError] = useState('')
  const [message, setMessage] = useState(location.state?.message || '')
  const [busy, setBusy] = useState(false)
  const [googleBusy, setGoogleBusy] = useState(false)
  const [title, subtitle, action] = content[mode]
  const token = new URLSearchParams(location.hash.slice(1)).get('token') || ''
  const update = event => {
    const { name, value, type, checked } = event.target
    setValues(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
    setErrors(prev => ({ ...prev, [name]: '' }))
    setError('')
  }
  async function submit(event) {
    event.preventDefault()
    if (busy) return
    const next = {}
    if (mode === 'register' && values.full_name.trim().length < 2) next.full_name = 'Please enter your full name.'
    if (mode !== 'reset' && !/^[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+$/.test(values.email.trim())) next.email = 'Enter a valid email address.'
    if (mode !== 'forgot') {
      if (!values.password) next.password = 'Enter your password.'
      else if (mode !== 'login' && values.password.length < 12) next.password = 'Use at least 12 characters.'
    }
    if (['register', 'reset'].includes(mode) && values.password !== values.confirm) next.confirm = 'Passwords do not match.'
    setErrors(next)
    if (Object.keys(next).length) return
    setBusy(true); setError(''); setMessage('')
    try {
      if (mode === 'login') {
        await login({ email: values.email.trim(), password: values.password, remember_me: values.remember_me })
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
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  async function googleLogin() {
    setGoogleBusy(true); setError(''); setMessage('')
    try { await loginWithGoogle() }
    catch (err) { setError(err.message || 'Google sign-in is unavailable. Please try again.'); setGoogleBusy(false) }
  }
  if (loading) return <div className="auth-status" role="status">Opening CareerNova…</div>
  if (user && mode !== 'reset') return <Navigate to="/" replace />
  return <main className="auth-page">
    <section className="auth-story" aria-label="Welcome to CareerNova">
      <Link to="/login" className="brand auth-brand"><span className="brand-mark"><Icon size={27} /></span><span>CareerNova<small>CAREER INTELLIGENCE</small></span></Link>
      <div className="auth-story-copy"><span className="auth-kicker"><span /> YOUR POTENTIAL. YOUR POSSIBILITIES.</span>
        <h1>A clearer path.<br /> A brighter <em>future.</em></h1>
        <p>Connect your skills, discover your strengths, and find a career direction that feels like you.</p>
      </div>
      <div className="auth-universe" aria-hidden="true"><div className="auth-orbit auth-orbit-outer" /><div className="auth-orbit" />
        <div className="auth-core"><Icon size={58} /><span>Your next chapter</span><small>STARTS WITH YOU</small></div>
        <div className="auth-float auth-float-skills"><span><Icon name="skill" /></span><div>Discover your skills<small>Recognize your potential</small></div></div>
        <div className="auth-float auth-float-career"><span><Icon name="career" /></span><div>Find your direction<small>Explore what comes next</small></div></div>
        <div className="auth-star auth-star-one">✦</div><div className="auth-star auth-star-two">✦</div>
      </div>
      <div className="auth-story-footer"><span className="auth-footer-line" /><p>Built for the journey ahead.<small>An AI-powered career research experience.</small></p></div>
    </section>
    <section className="auth-form-side">
      <div className="auth-form-top">{mode === 'login' ? <>New to CareerNova? <Link to="/register">Create an account <Icon name="arrow" size={15} /></Link></> : <>Already a member? <Link to="/login">Log in <Icon name="arrow" size={15} /></Link></>}</div>
      <div className="auth-form-card">
        <span className="auth-form-symbol"><Icon size={25} /></span><p className="eyebrow">YOUR CAREER STARTS HERE</p>
        <h2>{title}</h2><p className="auth-subtitle">{subtitle}</p>
        {['login', 'register'].includes(mode) && <>
          <button type="button" className="auth-google" onClick={googleLogin} disabled={busy || googleBusy}>
            <svg width="19" height="19" viewBox="0 0 24 24" aria-hidden="true"><path fill="#4285F4" d="M21.6 12.23c0-.71-.06-1.39-.18-2.05H12v3.88h5.38a4.6 4.6 0 0 1-2 3.02v2.51h3.24c1.89-1.74 2.98-4.3 2.98-7.36Z"/><path fill="#34A853" d="M12 22c2.7 0 4.96-.9 6.62-2.41l-3.24-2.51c-.9.6-2.04.97-3.38.97-2.6 0-4.8-1.76-5.59-4.12H3.07v2.59A10 10 0 0 0 12 22Z"/><path fill="#FBBC05" d="M6.41 13.93A6 6 0 0 1 6.1 12c0-.67.11-1.32.31-1.93V7.48H3.07A10 10 0 0 0 2 12c0 1.61.38 3.14 1.07 4.52l3.34-2.59Z"/><path fill="#EA4335" d="M12 5.95c1.47 0 2.79.51 3.83 1.51L18.7 4.6A9.6 9.6 0 0 0 12 2a10 10 0 0 0-8.93 5.48l3.34 2.59C7.2 7.71 9.4 5.95 12 5.95Z"/></svg>
            {googleBusy ? 'Connecting to Google…' : 'Continue with Google'}
          </button><div className="auth-divider"><span>or continue with email</span></div>
        </>}
        <form onSubmit={submit} noValidate>
          {message && <div className="auth-success" role="status"><Icon name="check" size={18} />{message}</div>}
          {error && <div className="auth-error" role="alert">{error}</div>}
          <fieldset disabled={busy || googleBusy}>
            {mode === 'register' && <div className="auth-field"><label htmlFor="full_name">Full name</label><input id="full_name" name="full_name" autoComplete="name" placeholder="Your full name" maxLength={100} value={values.full_name} onChange={update} required aria-invalid={!!errors.full_name} aria-describedby={errors.full_name ? 'name-error' : undefined} />{errors.full_name && <span className="auth-field-error" id="name-error">{errors.full_name}</span>}</div>}
            {mode !== 'reset' && <div className="auth-field"><label htmlFor="email">Email address</label><input id="email" name="email" type="email" autoComplete="email" placeholder="you@example.com" maxLength={254} value={values.email} onChange={update} required aria-invalid={!!errors.email} aria-describedby={errors.email ? 'email-error' : undefined} />{errors.email && <span className="auth-field-error" id="email-error">{errors.email}</span>}</div>}
            {mode !== 'forgot' && <><PasswordField name="password" label="Password" value={values.password} onChange={update} error={errors.password} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />{mode !== 'login' && <p className="auth-password-hint">Use at least 12 characters. A memorable passphrase works well.</p>}</>}
            {['register', 'reset'].includes(mode) && <PasswordField name="confirm" label="Confirm password" value={values.confirm} onChange={update} error={errors.confirm} autoComplete="new-password" />}
            {mode === 'login' && <div className="auth-options"><label><input name="remember_me" type="checkbox" checked={values.remember_me} onChange={update} /> Remember me</label><Link to="/forgot-password">Forgot password?</Link></div>}
            <button className="auth-submit" type="submit" disabled={busy}>{busy ? <><span className="auth-spinner" /> Please wait…</> : <>{action}<Icon name="arrow" size={18} /></>}</button>
          </fieldset>
        </form>
        <p className="auth-switch">{mode === 'login' ? <>Don’t have an account? <Link to="/register">Register now</Link></> : mode === 'register' ? <>Already have an account? <Link to="/login">Log in</Link></> : <Link to="/login">Back to login</Link>}</p>
        <div className="auth-reassurance"><svg width="15" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M12 2 3 6v6c0 6 9 10 9 10s9-4 9-10V6l-9-4Z" /><path d="m8 12 3 3 5-6" /></svg> Your next step, in a secure workspace.</div>
      </div>
      <footer className="auth-legal">CareerNova <span>© {new Date().getFullYear()} · University Research Project</span></footer>
    </section>
  </main>
}
