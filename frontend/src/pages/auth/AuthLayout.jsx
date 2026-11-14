// Shared shell for /login, /register, /forgot-password and /reset-password. The brand panel stays
// mounted; only the form side changes, sliding between routes. Motion's animation features are
// loaded with this chunk (not lazily), so entrance animations never wait on a second download.
import { useEffect, useState } from 'react'
import { Link, useLocation, useOutlet } from 'react-router-dom'
import { AnimatePresence, LazyMotion, MotionConfig, domAnimation, m } from 'motion/react'
import Icon from '../../components/Icon.jsx'
import ThemeToggle from '../../components/shell/ThemeToggle.jsx'
import { EASE } from '../home/motion.js'
import BrandPanel from './BrandPanel.jsx'
import './auth.css'

const slide = {
  initial: { opacity: 0, x: 28 },
  animate: { opacity: 1, x: 0, transition: { duration: 0.45, ease: EASE } },
  exit: { opacity: 0, x: -28, transition: { duration: 0.2, ease: 'easeIn' } },
}

// Ambient CSS animations pause while the tab is hidden.
function usePageHidden() {
  const [hidden, setHidden] = useState(() => typeof document !== 'undefined' && document.hidden)
  useEffect(() => {
    const update = () => setHidden(document.hidden)
    document.addEventListener('visibilitychange', update)
    return () => document.removeEventListener('visibilitychange', update)
  }, [])
  return hidden
}

export default function AuthLayout() {
  const location = useLocation()
  const outlet = useOutlet()
  const hidden = usePageHidden()
  const onLogin = location.pathname === '/login'
  return <LazyMotion features={domAnimation} strict><MotionConfig reducedMotion="user">
    <main className={`auth-shell ${hidden ? 'is-paused' : ''}`}>
      <BrandPanel />
      <section className="af-side">
        <div className="af-top">{onLogin
          ? <>New to CareerNova? <Link to="/register" className="af-nudge">Create an account <Icon name="arrow" size={15} /></Link></>
          : <>Already a member? <Link to="/login" className="af-nudge">Log in <Icon name="arrow" size={15} /></Link></>}
          <ThemeToggle className="af-theme" /></div>
        <div className="af-stage">
          <AnimatePresence mode="wait" initial={false}>
            <m.div key={location.pathname} className="af-route" variants={slide} initial="initial" animate="animate" exit="exit">{outlet}</m.div>
          </AnimatePresence>
        </div>
        <footer className="af-legal">CareerNova <span>© {new Date().getFullYear()} · University Research Project</span></footer>
      </section>
    </main>
  </MotionConfig></LazyMotion>
}
