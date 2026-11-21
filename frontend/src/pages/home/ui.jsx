// Small building blocks shared by the Home sections.
import { useEffect, useId, useRef, useState } from 'react'
import { AnimatePresence, m } from 'motion/react'
import Icon from '../../components/Icon.jsx'
import { useCountUp } from './useCountUp.js'
import { formatPercent } from './marketApi.js'
import { swapVariants } from './motion.js'
import { useInViewport } from './viewport.js'

// Equal-width segmented control. The pill slides with a transform, so nothing re-lays out.
// Arrow keys move between options, as in a native radio group.
export function Segmented({ label, options, value, onChange, dark = false, className = '' }) {
  const index = Math.max(0, options.findIndex(option => option.value === value))
  const group = useRef(null)
  function onKeyDown(event) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
    event.preventDefault()
    const enabled = options.map((option, i) => (option.disabled ? null : i)).filter(i => i != null)
    const at = enabled.indexOf(index)
    const next = event.key === 'Home' ? enabled[0] : event.key === 'End' ? enabled[enabled.length - 1]
      : enabled[(at + (event.key === 'ArrowRight' ? 1 : -1) + enabled.length) % enabled.length]
    onChange(options[next].value)
    group.current?.querySelectorAll('button')[next]?.focus()
  }
  return <div ref={group} className={`segmented ${dark ? 'is-dark' : ''} ${className}`} role="group" aria-label={label} style={{ '--n': options.length }} onKeyDown={onKeyDown}>
    <span className="segmented-pill" aria-hidden="true" style={{ transform: `translateX(${index * 100}%)` }} />
    {options.map(option => <button key={option.value} type="button" aria-pressed={option.value === value} disabled={option.disabled}
      tabIndex={option.value === value ? 0 : -1} title={option.title} onClick={() => onChange(option.value)}
      className={option.value === value ? 'is-active' : ''}>{option.label}{option.extra != null && <small>{option.extra}</small>}</button>)}
  </div>
}

// An "i" button whose note shows on hover, focus or tap, and is always linked for screen readers.
export function InfoTip({ label = 'About this data', children, dark = false }) {
  const id = useId()
  const [open, setOpen] = useState(false)
  return <span className={`infotip ${dark ? 'is-dark' : ''} ${open ? 'is-open' : ''}`}>
    <button type="button" aria-label={label} aria-describedby={id} aria-expanded={open} onClick={() => setOpen(value => !value)} onBlur={() => setOpen(false)}>
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 11v5 M12 8h.01" /></svg>
    </button>
    <span role="tooltip" id={id} className="infotip-body">{children}</span>
  </span>
}

// Counts towards `value` once the element has been on screen.
export function CountUp({ value, format = v => Math.round(v).toLocaleString('en-US'), className = '' }) {
  const ref = useRef(null)
  const seen = useInViewport(ref, { once: true, amount: 0.4 })
  const shown = useCountUp(value, { active: seen })
  return <span ref={ref} className={`count ${className}`}>{value == null ? '—' : format(seen ? shown : 0)}</span>
}

// Growth change with an arrow and sign, so the direction never depends on colour alone.
export function Delta({ growth }) {
  if (growth?.pct == null) {
    const text = growth?.reason === 'low_volume' ? 'Too few postings' : 'Collecting data'
    const why = growth?.reason === 'low_volume' ? 'Fewer than 5 postings in the previous week, so a percentage would be misleading.'
      : growth?.reason === 'gap' ? 'Collection missed more than 6 days, so the two weeks cannot be compared fairly.'
        : 'Growth needs 14 days of collected postings.'
    return <span className="pill pill-neutral" title={why}>{text}<span className="sr-only">: {why}</span></span>
  }
  const word = growth.direction === 'up' ? 'Up' : growth.direction === 'down' ? 'Down' : 'No change'
  return <span className={`delta is-${growth.direction}`}>
    <svg width="9" height="9" viewBox="0 0 10 10" aria-hidden="true">{growth.direction === 'flat' ? <rect x="1" y="4" width="8" height="2" rx="1" /> : <path d={growth.direction === 'up' ? 'M5 1 9.5 9h-9Z' : 'M5 9 .5 1h9Z'} />}</svg>
    <span className="sr-only">{word} </span>{formatPercent(growth.pct)}
  </span>
}

// Line sparkline that draws itself (a clip that scales open) and, when interactive, shows the
// exact value under the pointer. Values only; nothing is drawn when there are fewer than two points.
export function Sparkline({ values, labels = [], width = 96, height = 26, format = String, interactive = false, className = '' }) {
  const ref = useRef(null)
  const seen = useInViewport(ref, { once: true, amount: 0.6 })
  const [hover, setHover] = useState(null)
  const clip = useId().replace(/:/g, '')
  const max = Math.max(...values, 0)
  if (values.length < 2 || max === 0) return <span className="spark-empty" aria-hidden="true">—</span>
  const x = i => 2 + (i / (values.length - 1)) * (width - 4)
  const y = v => height - 3 - (v / max) * (height - 7)
  const points = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  const last = values.length - 1
  return <span className={`spark ${className}`} ref={ref}>
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true"
      onPointerMove={interactive ? event => { const box = event.currentTarget.getBoundingClientRect(); setHover(Math.round(((event.clientX - box.left) / box.width) * last)) } : undefined}
      onPointerLeave={interactive ? () => setHover(null) : undefined}>
      <defs><clipPath id={clip}><rect className={`spark-clip ${seen ? 'is-in' : ''}`} x="0" y="0" width={width} height={height} /></clipPath></defs>
      <g clipPath={`url(#${clip})`}>
        <polyline points={points} />
        <circle cx={x(last)} cy={y(values[last])} r="2.6" />
      </g>
      {hover != null && <circle className="spark-hover" cx={x(hover)} cy={y(values[hover])} r="3.5" />}
    </svg>
    {hover != null && <span className="spark-tip" style={{ left: `${(x(hover) / width) * 100}%` }}><strong>{format(values[hover])}</strong>{labels[hover] && <span>{labels[hover]}</span>}</span>}
  </span>
}

// Show/hide region whose content fades and rises in (height changes instantly; nothing else moves).
export function Disclosure({ summary, children, className = '' }) {
  const [open, setOpen] = useState(false)
  const id = useId()
  return <div className={`disclosure ${className}`}>
    <button type="button" className="disclosure-toggle" aria-expanded={open} aria-controls={id} onClick={() => setOpen(value => !value)}>
      <span className="disclosure-chevron" aria-hidden="true"><Icon name="arrow" size={13} /></span>{summary}
    </button>
    <AnimatePresence initial={false}>
      {open && <m.div id={id} className="disclosure-body" variants={swapVariants} initial="initial" animate="enter" exit="exit">{children}</m.div>}
    </AnimatePresence>
  </div>
}

// Card heading used by every bento card.
export function CardHeader({ title, hint, children, id }) {
  return <header className="card-head"><div><h3 id={id}>{title}</h3>{hint && <p>{hint}</p>}</div>{children && <div className="card-head-tools">{children}</div>}</header>
}

// Fires once when the element first scrolls into view (used to start CSS-driven bar growth).
export function useSeen(amount = 0.2) {
  const ref = useRef(null)
  const seen = useInViewport(ref, { once: true, amount })
  return [ref, seen]
}

// Width of an element, kept up to date (charts draw at their real pixel size).
export function useWidth() {
  const ref = useRef(null)
  const [width, setWidth] = useState(0)
  useEffect(() => {
    if (!ref.current) return undefined
    const observer = new ResizeObserver(([entry]) => setWidth(Math.round(entry.contentRect.width)))
    observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])
  return [ref, width]
}
