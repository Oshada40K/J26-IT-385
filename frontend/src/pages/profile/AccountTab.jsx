// Account and security: change password (email accounts only) and log out of this device.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Icon from '../../components/Icon.jsx'
import { useAuth } from '../../auth/AuthContext.jsx'
import { changePassword } from './profileApi.js'
import { passwordStrength } from './profileModel.js'
import { Field, describedBy } from './profileUi.jsx'

export default function AccountTab({ account, toast }) {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [leaving, setLeaving] = useState(false)

  async function signOut() {
    setLeaving(true)
    try { await logout(); navigate('/login', { replace: true }) }
    catch (error) { toast(error.message || 'Could not log out. Please try again.', 'error'); setLeaving(false) }
  }

  return <div className="pf-stack">
    <section className="card pf-card" aria-labelledby="pf-signin">
      <header className="card-head"><div><h3 id="pf-signin">Sign-in method</h3></div></header>
      {account.provider === 'google'
        ? <p className="pf-provider"><span className="pf-provider-mark" aria-hidden="true">G</span>
          <span>You sign in with <strong>Google</strong> as {account.email}. Your password is managed by Google, so there is nothing to change here.</span></p>
        : <PasswordForm toast={toast} />}
    </section>
    <section className="card pf-card" aria-labelledby="pf-session">
      <header className="card-head"><div><h3 id="pf-session">This device</h3><p>Ends your session in this browser only.</p></div></header>
      <button type="button" className="button-secondary" onClick={signOut} disabled={leaving}><Icon name="arrow" size={15} />{leaving ? 'Logging out…' : 'Log out of this device'}</button>
    </section>
  </div>
}

function PasswordForm({ toast }) {
  const empty = { current: '', next: '', confirm: '' }
  const [form, setForm] = useState(empty)
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [show, setShow] = useState(false)
  const strength = passwordStrength(form.next)
  const set = field => event => { setForm(current => ({ ...current, [field]: event.target.value })); setErrors(current => ({ ...current, [field]: undefined, form: undefined })) }

  async function submit(event) {
    event.preventDefault()
    const found = {}
    if (!form.current) found.current = 'Enter your current password.'
    if (form.next.length < 12) found.next = 'Use at least 12 characters.'
    else if (form.next === form.current) found.next = 'Choose a password that is different from the current one.'
    if (form.confirm !== form.next) found.confirm = 'The passwords do not match.'
    setErrors(found)
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      await changePassword(form.current, form.next)
      setForm(empty)
      toast('Password changed. Other devices have been signed out.')
    } catch (error) {
      if (/current password/i.test(error.message)) setErrors({ current: error.message })
      else setErrors({ form: error.message })
    } finally { setSaving(false) }
  }

  const field = (key, label, autoComplete, hint) => <Field id={`pf-pw-${key}`} label={label} error={errors[key]} hint={hint}>
    <input id={`pf-pw-${key}`} type={show ? 'text' : 'password'} value={form[key]} onChange={set(key)} autoComplete={autoComplete}
      aria-invalid={Boolean(errors[key])} aria-describedby={describedBy(`pf-pw-${key}`, errors[key], hint)} />
  </Field>

  return <form className="pf-password" onSubmit={submit} noValidate aria-label="Change password">
    <p className="pf-muted">Changing your password signs you out on every other device.</p>
    {field('current', 'Current password', 'current-password')}
    {field('next', 'New password', 'new-password', 'At least 12 characters. A short sentence works well.')}
    {form.next && <div className="pf-strength" data-score={strength.score}>
      <span className="pf-strength-bar" aria-hidden="true">{[1, 2, 3, 4].map(step => <i key={step} className={strength.score >= step ? 'is-on' : ''} />)}</span>
      <span aria-live="polite">Strength: <strong>{strength.label}</strong></span>
    </div>}
    {field('confirm', 'Confirm new password', 'new-password')}
    <label className="pf-check"><input type="checkbox" checked={show} onChange={event => setShow(event.target.checked)} />Show passwords</label>
    {errors.form && <p className="pf-error" role="alert">{errors.form}</p>}
    <div className="pf-form-actions"><button type="submit" disabled={saving}>{saving ? 'Changing…' : 'Change password'}</button></div>
  </form>
}
