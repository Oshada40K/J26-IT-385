// Animates only the routed content area; the sidebar, navbar and footer stay mounted.
// The old page fades out before the new one fades in, and the scroll position is reset
// between them (or restored on back/forward), so the new page never renders mid-scroll.
import { useEffect, useLayoutEffect, useRef } from 'react'
import { useLocation, useNavigationType } from 'react-router-dom'
import { AnimatePresence, LazyMotion, m, useReducedMotion } from 'motion/react'

const loadFeatures = () => import('./motionFeatures.js').then(module => module.default)
const EASE = [0.2, 0.75, 0.25, 1]
const slide = {
  initial: { opacity: 0, y: 10 },
  enter: { opacity: 1, y: 0, transition: { duration: 0.26, ease: EASE } },
  exit: { opacity: 0, y: -6, transition: { duration: 0.14, ease: 'easeIn' } },
}
// Reduced motion: a short cross-fade with no movement at all.
const fade = {
  initial: { opacity: 0 },
  enter: { opacity: 1, transition: { duration: 0.2 } },
  exit: { opacity: 0, transition: { duration: 0.12 } },
}

export default function PageTransition({ children }) {
  const location = useLocation()
  const navigationType = useNavigationType()
  const variants = useReducedMotion() ? fade : slide
  const positions = useRef(new Map())
  const latest = useRef({ key: location.key, type: navigationType })
  latest.current = { key: location.key, type: navigationType }

  useEffect(() => {
    if ('scrollRestoration' in window.history) window.history.scrollRestoration = 'manual'
  }, [])

  // Remember where each history entry was scrolled to when leaving it.
  useLayoutEffect(() => {
    const { key } = location
    return () => { positions.current.set(key, window.scrollY) }
  }, [location])

  function placeScroll() {
    const { key, type } = latest.current
    window.scrollTo(0, type === 'POP' ? positions.current.get(key) ?? 0 : 0)
  }

  return <LazyMotion features={loadFeatures} strict>
    <AnimatePresence mode="wait" initial={false} onExitComplete={placeScroll}>
      <m.div key={location.pathname} variants={variants} initial="initial" animate="enter" exit="exit">
        {children(location)}
      </m.div>
    </AnimatePresence>
  </LazyMotion>
}
