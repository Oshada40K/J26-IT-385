// Wraps the Home page so every Motion animation respects prefers-reduced-motion:
// transforms are dropped and only opacity fades remain. Reveal is the shared section entrance.
import { useRef } from 'react'
import { MotionConfig, useReducedMotion } from 'motion/react'
import { DURATION, EASE, VIEWPORT } from './motion.js'
import { useInViewport } from './viewport.js'

export { useReducedMotion }

export default function MotionRoot({ children }) {
  return <MotionConfig reducedMotion="user" transition={{ duration: DURATION.ui, ease: EASE }}>{children}</MotionConfig>
}

// Fade + rise once 20% of the element is visible; children marked with RevealItem stagger in.
// Plain CSS (home.css, "Reveal"), not Motion: Motion's features load lazily, and a section that
// is already on screen when the page opens asked to animate before they arrived and stayed
// hidden. The CSS animation fills backwards only, so it leaves no styles behind (hover lifts keep
// working), and the global reduced-motion rule shows everything at once.
export function Reveal({ as: Tag = 'div', className = '', children, ...props }) {
  const ref = useRef(null)
  const seen = useInViewport(ref, VIEWPORT)
  return <Tag ref={ref} className={`reveal ${seen ? 'is-in' : ''} ${className}`} {...props}>{children}</Tag>
}

export function RevealItem({ as: Tag = 'div', className = '', children, ...props }) {
  return <Tag className={`reveal-item ${className}`} {...props}>{children}</Tag>
}
