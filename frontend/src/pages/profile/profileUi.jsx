// Small building blocks for the profile page: tabs, toasts, a confirmation modal, form fields,
// the completeness ring and module empty states.
import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { AnimatePresence, m } from 'motion/react'
import Icon from '../../components/Icon.jsx'
import { swapVariants } from '../home/motion.js'

// Portalled layers keep the page's colour tokens and theme.
export function Layer({ theme, children }) {
  return createPortal(<div className="cn-home cn-layer" data-theme={theme}>{children}</div>, document.body)
}

// Keyboard: arrows move between tabs, Home/End jump to the ends (WAI-ARIA tabs pattern).
export function Tabs({ tabs, value, onChange, idPrefix }) {
  const refs = useRef({})
  function onKey(event, index) {
    const keys = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: tabs.length - 1 }
    if (!(event.key in keys)) return
    event.preventDefault()
    const next = tabs[(keys[event.key] + tabs.length) % tabs.length]
    onChange(next.value)
    refs.current[next.value]?.focus()
  }
  return <div className="pf-tabs" role="tablist" aria-label="Profile sections">
    {tabs.map((tab, index) => <button key={tab.value} ref={el => { refs.current[tab.value] = el }} type="button" role="tab"
      id={`${idPrefix}-tab-${tab.value}`} aria-controls={`${idPrefix}-panel-${tab.value}`} aria-selected={value === tab.value}
      tabIndex={value === tab.value ? 0 : -1} className={value === tab.value ? 'is-active' : ''}
      onClick={() => onChange(tab.value)} onKeyDown={event => onKey(event, index)}>
      {tab.label}{tab.badge && <span className="pf-tab-badge" aria-label={tab.badgeLabel}>{tab.badge}</span>}
    </button>)}
  </div>
}

export function useToasts() {
  const [items, setItems] = useState([])
  const push = useCallback((text, tone = 'success') => {
    const id = `${Date.now()}-${Math.random()}`
    setItems(list => [...list.slice(-2), { id, text, tone }])
    setTimeout(() => setItems(list => list.filter(item => item.id !== id)), tone === 'error' ? 7000 : 4000)
  }, [])
  const dismiss = useCallback(id => setItems(list => list.filter(item => item.id !== id)), [])
  return { items, push, dismiss }
}

export function Toasts({ items, dismiss, theme }) {
  return <Layer theme={theme}><div className="pf-toasts" role="status" aria-live="polite">
    <AnimatePresence initial={false}>
      {items.map(item => <m.div key={item.id} className={`pf-toast is-${item.tone}`} variants={swapVariants} initial="initial" animate="enter" exit="exit">
        <Icon name={item.tone === 'error' ? 'alert' : 'check'} size={16} /><span>{item.text}</span>
        <button type="button" className="pf-icon-button" aria-label="Dismiss message" onClick={() => dismiss(item.id)}><Icon name="close" size={14} /></button>
      </m.div>)}
    </AnimatePresence>
  </div></Layer>
}

// Modal dialog: focus moves inside, Tab stays inside, Escape and the backdrop close it,
// and focus returns to the element that opened it.
export function Modal({ title, description, onClose, children, theme }) {
  const titleId = useId()
  const descriptionId = useId()
  const panel = useRef(null)
  useEffect(() => {
    const opener = document.activeElement
    panel.current?.querySelector('input, button:not([disabled])')?.focus()
    const onKey = event => {
      if (event.key === 'Escape') { event.preventDefault(); onClose() }
      if (event.key !== 'Tab') return
      const focusable = [...panel.current.querySelectorAll('input, button:not([disabled]), a[href]')]
      const first = focusable[0], last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('keydown', onKey); opener?.focus?.() }
  }, [onClose])
  return <Layer theme={theme}><div className="pf-modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <m.div ref={panel} className="pf-modal" role="dialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={descriptionId}
      initial={{ opacity: 0, y: 12, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}>
      <h2 id={titleId}>{title}</h2>
      <div id={descriptionId}>{description}</div>
      {children}
    </m.div>
  </div></Layer>
}

export function Field({ id, label, hint, error, optional, counter, children }) {
  return <div className={`pf-field ${error ? 'has-error' : ''}`}>
    <label htmlFor={id}>{label}{optional && <span className="pf-optional">Optional</span>}</label>
    {children}
    <div className="pf-field-foot">
      {error ? <p className="pf-error" id={`${id}-error`}>{error}</p> : hint ? <p className="pf-hint" id={`${id}-hint`}>{hint}</p> : <span />}
      {counter}
    </div>
  </div>
}

// aria-describedby for a Field's control.
export const describedBy = (id, error, hint) => error ? `${id}-error` : hint ? `${id}-hint` : undefined

export function Ring({ percent, size = 92 }) {
  const radius = (size - 10) / 2
  const length = 2 * Math.PI * radius
  return <div className="pf-ring" role="img" aria-label={`Profile ${percent}% complete`} style={{ width: size, height: size }}>
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
      <circle className="pf-ring-track" cx={size / 2} cy={size / 2} r={radius} />
      <circle className="pf-ring-value" cx={size / 2} cy={size / 2} r={radius} strokeDasharray={length}
        style={{ strokeDashoffset: length * (1 - percent / 100) }} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
    </svg>
    <span aria-hidden="true"><strong>{percent}%</strong><small>complete</small></span>
  </div>
}

export function EmptyModule({ text, to, action, icon }) {
  return <div className="pf-empty"><span className="pf-empty-icon"><Icon name={icon} size={18} /></span>
    <p>{text}</p><Link className="button pf-button-sm" to={to}>{action}</Link></div>
}

export const formatDate = value => value ? new Date(value).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : null
