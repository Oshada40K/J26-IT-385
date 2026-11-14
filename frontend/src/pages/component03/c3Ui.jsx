// Small building blocks for the Career prediction page: scroll reveal (once), tooltips,
// count-up numbers and an accordion. Animation is CSS (transform/opacity), started by a class
// when the element is first seen; the global reduced-motion rule turns it off.
import { useId, useRef, useState } from 'react'
import { useInViewport } from '../home/viewport.js'
import { useCountUp } from '../home/useCountUp.js'

// Fires once when the element is first on screen.
export function useSeen(amount = 0.2) {
  const ref = useRef(null)
  return [ref, useInViewport(ref, { amount, once: true })]
}

// A page section that rises in once. `id` is used by the section nav.
export function Section({ id, className = '', children, amount = 0.12, as: Tag = 'section', ...props }) {
  const [ref, seen] = useSeen(amount)
  return <Tag ref={ref} id={id} className={`c3-reveal ${seen ? 'is-in' : ''} ${className}`} {...props}>{children}</Tag>
}

// Hover/focus tooltip. The trigger is focusable and described by the tip.
export function Tip({ text, children, className = '', as: Tag = 'span' }) {
  const id = useId()
  return <Tag className={`c3-tip ${className}`} tabIndex={0} aria-describedby={id}>
    {children}<span role="tooltip" id={id} className="c3-tip-body">{text}</span>
  </Tag>
}

// Counts from 0 once `active` (critically damped; reduced motion jumps straight to the value).
export function Count({ value, active, decimals = 0, suffix = '' }) {
  const shown = useCountUp(value, { active })
  return <>{(active ? shown : 0).toFixed(decimals)}{suffix}</>
}

export function Accordion({ title, children, className = '' }) {
  const [open, setOpen] = useState(false)
  const id = useId()
  return <div className={`c3-accordion ${open ? 'is-open' : ''} ${className}`}>
    <button type="button" className="c3-accordion-button" aria-expanded={open} aria-controls={id} onClick={() => setOpen(value => !value)}>
      <span>{title}</span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
    </button>
    <div id={id} className="c3-accordion-body" hidden={!open}>{children}</div>
  </div>
}

// Check / minus icons that draw themselves (stroke draw, small SVG).
export function Mark({ down }) {
  return <svg className="c3-mark" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d={down ? 'M6 12h12' : 'm5 12.5 4.5 4.5L19 7.5'} pathLength="1" />
  </svg>
}
