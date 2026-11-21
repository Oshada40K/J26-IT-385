// Home: CV upload and career journey on top, the live Career Market Pulse below (loaded when
// it comes near the viewport), and a closing call to action. Presentation only: uploads, API
// calls and routes are the same as before.
import { lazy, useCallback, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { m } from 'motion/react'
import { useAuth } from '../auth/AuthContext.jsx'
import { Bone } from '../components/loading/Skeletons.jsx'
import Icon from '../components/Icon.jsx'
import { useHomeTheme } from '../components/shell/theme.js'
import MotionRoot, { useReducedMotion } from './home/MotionRoot.jsx'
import HeroUpload from './home/HeroUpload.jsx'
import JourneyStepper from './home/JourneyStepper.jsx'
import CtaBand from './home/CtaBand.jsx'
import LazySection from './home/LazySection.jsx'
import { useInViewport } from './home/viewport.js'
import { refreshJourney, useJourney } from './home/journey.js'
import { firstName, greeting } from './home/homeUtils.js'
import { wordVariants, wordsVariants } from './home/motion.js'
import './home/home.css'

const MarketPulse = lazy(() => import('./home/MarketPulse.jsx'))
const HEADLINE = [['Big', 'possibilities.'], ['Start', 'with', 'your', 'CV.']]

function PulsePlaceholder() {
  return <div className="pulse-placeholder" aria-hidden="true">
    <div className="mp-hero"><Bone w={180} h={10} /><Bone w="45%" h={22} className="sk-gap" /><div className="mp-kpis">{[0, 1, 2, 3].map(i => <div key={i} className="kpi"><Bone w="50%" h={10} /><Bone w="60%" h={26} className="sk-gap" /></div>)}</div></div>
  </div>
}

export default function Home() {
  const theme = useHomeTheme()
  const reduced = useReducedMotion()
  const { user } = useAuth()
  const journey = useJourney()
  const location = useLocation()
  const aurora = useRef(null)
  const auroraVisible = useInViewport(aurora) // the background animation pauses off-screen

  useEffect(() => { refreshJourney() }, [])

  // Scroll to a section requested by the command palette or by navigation state. Market
  // sections load lazily, so wait briefly for them to appear after scrolling towards them.
  const scrollTo = useCallback(id => {
    const go = element => element.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' })
    const target = document.getElementById(id)
    if (target) { go(target); return }
    const area = document.getElementById('market-area')
    if (area) go(area)
    let tries = 0
    const timer = setInterval(() => {
      const found = document.getElementById(id)
      if (found) { clearInterval(timer); go(found) } else if (++tries > 40) clearInterval(timer)
    }, 100)
  }, [reduced])
  useEffect(() => {
    const onRequest = event => scrollTo(event.detail)
    window.addEventListener('careernova:scroll-to', onRequest)
    return () => window.removeEventListener('careernova:scroll-to', onRequest)
  }, [scrollTo])
  useEffect(() => {
    if (!location.state?.scrollTo) return undefined
    const timer = setTimeout(() => scrollTo(location.state.scrollTo), 350) // after the page transition
    return () => clearTimeout(timer)
  }, [location.state, scrollTo])

  const focusUpload = useCallback(() => {
    document.getElementById('cv-upload')?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'center' })
    setTimeout(() => document.getElementById('cv-choose')?.focus({ preventScroll: true }), reduced ? 0 : 400)
  }, [reduced])

  const name = firstName(user?.full_name)
  return <MotionRoot>
    <div className="page cn-home" data-theme={theme}>
      <section className="hero" aria-labelledby="home-title">
        <div ref={aurora} className={`hero-aurora ${auroraVisible ? '' : 'is-paused'}`} aria-hidden="true"><i /><i /><i /><span className="sparkle s1"><Icon size={14} /></span><span className="sparkle s2"><Icon size={10} /></span><span className="sparkle s3"><Icon size={12} /></span></div>
        <div className="home-hero-copy">
          <p className="hero-greeting">{greeting()}{name && `, ${name}`} <span aria-hidden="true">👋</span></p>
          <m.h1 id="home-title" aria-label="Big possibilities. Start with your CV." variants={wordsVariants} initial="hidden" animate="show">
            {HEADLINE.map((line, lineIndex) => <span key={lineIndex} className={`hero-line ${lineIndex ? 'is-accent' : ''}`} aria-hidden="true">
              {line.map(word => <m.span key={word} className="hero-word" variants={wordVariants}>{word} </m.span>)}
            </span>)}
          </m.h1>
        </div>
        <div className="hero-grid">
          <HeroUpload />
          <JourneyStepper journey={journey} onStartHere={focusUpload} />
        </div>
      </section>
      <LazySection id="market-area" minHeight={720} fallback={<PulsePlaceholder />}>
        <MarketPulse />
      </LazySection>
      <CtaBand journey={journey} onUpload={focusUpload} />
    </div>
  </MotionRoot>
}
