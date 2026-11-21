// Form controls for the auth card: floating-label fields with a leading icon and a focus ring
// that draws around the field, a password field with an animated eye and a Caps Lock warning,
// and a checkbox whose tick draws in. Labels stay real <label>s for screen readers and tests.
import { useId, useState } from 'react'
import { AnimatePresence, m } from 'motion/react'

const ICONS = {
  mail: 'M4 6h16v12H4z M4 7l8 6 8-6',
  lock: 'M6 11h12v9H6z M8.5 11V8a3.5 3.5 0 0 1 7 0v3',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z M4.5 20a7.5 7.5 0 0 1 15 0',
}
export function FieldIcon({ name }) {
  return <svg className="af-lead" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={ICONS[name]} /></svg>
}

// The ring is an SVG outline drawn with a gradient stroke when the field is focused.
function Ring() {
  const id = `af-ring-${useId().replace(/:/g, '')}`
  return <svg className="af-ring" aria-hidden="true" preserveAspectRatio="none">
    <defs><linearGradient id={id} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#4F46E5" /><stop offset=".55" stopColor="#7C3AED" /><stop offset="1" stopColor="#22D3EE" /></linearGradient></defs>
    <rect pathLength="1" stroke={`url(#${id})`} />
  </svg>
}

export function FieldError({ id, message }) {
  return <AnimatePresence initial={false}>{message && <m.span key={message} className="af-field-error" id={id}
    initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>{message}</m.span>}</AnimatePresence>
}

export function TextField({ name, label, icon, error, valid, ...input }) {
  const errorId = `${name}-error`
  return <div className={`af-field ${error ? 'has-error' : ''}`}>
    <div className="af-control">
      <FieldIcon name={icon} />
      <input id={name} name={name} className="af-input" placeholder=" " aria-invalid={!!error} aria-describedby={error ? errorId : undefined} {...input} />
      <label htmlFor={name}>{label}</label>
      <AnimatePresence>{valid && !error && <m.span className="af-valid" aria-hidden="true" initial={{ scale: 0, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 520, damping: 22 }}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12.5 4.5 4.5L19 7.5" /></svg>
      </m.span>}</AnimatePresence>
      <Ring />
    </div>
    <FieldError id={errorId} message={error} />
  </div>
}

export function PasswordField({ name, label, value, onChange, error, autoComplete }) {
  const [visible, setVisible] = useState(false)
  const [caps, setCaps] = useState(false)
  const errorId = `${name}-error`
  const capsId = `${name}-caps`
  const readCaps = event => setCaps(Boolean(event.getModifierState?.('CapsLock')))
  return <div className={`af-field ${error ? 'has-error' : ''}`}>
    <div className="af-control">
      <FieldIcon name="lock" />
      <input id={name} name={name} className="af-input" type={visible ? 'text' : 'password'} value={value} onChange={onChange} placeholder=" "
        autoComplete={autoComplete} maxLength={128} required aria-invalid={!!error}
        aria-describedby={[error && errorId, caps && capsId].filter(Boolean).join(' ') || undefined}
        onKeyDown={readCaps} onKeyUp={readCaps} onBlur={() => setCaps(false)} />
      <label htmlFor={name}>{label}</label>
      <button type="button" className={`af-eye ${visible ? 'is-open' : ''}`} aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`} aria-pressed={visible} onClick={() => setVisible(v => !v)}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden="true">
          <path className="af-eye-lid" d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
          <circle className="af-eye-pupil" cx="12" cy="12" r="3" />
          <path className="af-eye-slash" d="m3.5 3.5 17 17" pathLength="1" />
        </svg>
      </button>
      <Ring />
    </div>
    <AnimatePresence initial={false}>{caps && <m.span key="caps" id={capsId} className="af-caps" aria-live="polite"
      initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 4 4 12h4v5h8v-5h4z M8 20h8" /></svg>
      Caps Lock is on</m.span>}</AnimatePresence>
    <FieldError id={errorId} message={error} />
  </div>
}

export function Checkbox({ name, checked, onChange, children }) {
  return <label className="af-check">
    <input type="checkbox" name={name} checked={checked} onChange={onChange} />
    <span className="af-check-box" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12.5 4.5 4.5L19 7.5" pathLength="1" /></svg></span>
    {children}
  </label>
}
