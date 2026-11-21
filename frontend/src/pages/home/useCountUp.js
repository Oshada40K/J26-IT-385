// Animates a number towards its target with a critically damped spring (no overshoot), so
// figures count up on first view and count up or down when the market changes.
// Reduced motion: the target is shown at once.
import { useEffect, useRef, useState } from 'react'
import { useReducedMotion } from 'motion/react'

const settle = t => 1 - (1 + 8 * t) * Math.exp(-8 * t) // spring position for normalised time 0..1

export function useCountUp(target, { active = true, duration = 900 } = {}) {
  const reduced = useReducedMotion()
  const [value, setValue] = useState(0)
  const current = useRef(0)
  useEffect(() => {
    if (target == null || !active) return undefined
    const from = current.current
    if (reduced || from === target) { current.current = target; setValue(target); return undefined }
    const started = performance.now()
    let frame
    const tick = now => {
      const t = Math.min((now - started) / duration, 1)
      const next = t >= 1 ? target : from + (target - from) * settle(t)
      current.current = next
      setValue(next)
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target, active, reduced, duration])
  return target == null ? null : value
}
