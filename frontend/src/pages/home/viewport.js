// Tells Home components when their element is on screen, without IntersectionObserver.
//
// Why not IntersectionObserver: while any observer is active, Chromium produces a main-thread
// frame for every frame of every running compositor animation. Home has calm looping effects
// (aurora, sparkles, the live dot), so a pending observer turned each of them into constant
// style work, about 20% of a throttled phone CPU each. This watcher measures only when the page
// scrolls or resizes, or when an element starts being watched, so an idle page does no work.
import { useEffect, useState } from 'react'

const watched = new Set()
let frame = 0
let listening = false

// `amount` is the share of the element (or of the viewport, for elements taller than it) that
// must be visible; 0 means any part. `margin` grows the viewport, like a rootMargin.
function isInView({ el, amount, margin }) {
  const rect = el.getBoundingClientRect()
  if (!rect.width && !rect.height) return false // not rendered
  const height = window.innerHeight
  if (rect.right < -margin || rect.left > window.innerWidth + margin) return false
  const visible = Math.min(rect.bottom, height + margin) - Math.max(rect.top, -margin)
  if (amount === 0) return visible > 0 || (visible === 0 && rect.height === 0)
  return visible >= amount * Math.min(rect.height, height)
}

function check() {
  frame = 0
  for (const entry of [...watched]) {
    const inView = isInView(entry)
    if (inView !== entry.inView) { entry.inView = inView; entry.onChange(inView) }
  }
}

function schedule() { if (!frame) frame = requestAnimationFrame(check) }

function setListening(on) {
  if (on === listening) return
  listening = on
  const method = on ? 'addEventListener' : 'removeEventListener'
  window[method]('scroll', schedule, { passive: true })
  window[method]('resize', schedule, { passive: true })
}

export function watchViewport(el, { amount = 0, margin = 0 } = {}, onChange) {
  const entry = { el, amount, margin, onChange, inView: undefined }
  watched.add(entry)
  setListening(true)
  schedule()
  return () => {
    watched.delete(entry)
    if (!watched.size) { setListening(false); cancelAnimationFrame(frame); frame = 0 }
  }
}

// React hook: true while the element is in view. With `once`, it stays true and stops watching.
export function useInViewport(ref, { amount = 0, margin = 0, once = false } = {}) {
  const [inView, setInView] = useState(false)
  const done = once && inView
  useEffect(() => {
    const el = ref.current
    if (!el || done) return undefined
    let stop = () => {}
    stop = watchViewport(el, { amount, margin }, value => {
      setInView(value)
      if (once && value) stop()
    })
    return () => stop()
  }, [ref, amount, margin, once, done])
  return inView
}
