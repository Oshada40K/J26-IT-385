// Left brand panel shared by every auth page: aurora + star field with pointer parallax, the
// word-by-word headline, and the orbit that tells the four-step journey. Decorative parts are
// aria-hidden; the readable copy stays plain text. Ambient motion is CSS (paused with the tab).
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, m, useReducedMotion } from 'motion/react'
import Icon from '../../components/Icon.jsx'
import { EASE } from '../home/motion.js'

const STEPS = [
  { key: 'skills', label: 'Skills', icon: 'skill', title: 'Discover your skills', note: 'Recognize your potential', spot: 'tl', line: 'M30 17 L43 40' },
  { key: 'personality', label: 'Personality', icon: 'personality', title: 'Understand your personality', note: 'See how you like to work', spot: 'tr', line: 'M70 25 L57 41' },
  { key: 'career', label: 'Career', icon: 'career', title: 'Find your direction', note: 'Explore what comes next', spot: 'br', line: 'M70 83 L57 60' },
  { key: 'roadmap', label: 'Roadmap', icon: 'roadmap', title: 'Follow your roadmap', note: 'Step by step, at your pace', spot: 'bl', line: 'M30 75 L43 59' },
]
// Slow glowing motes that drift upward, and three shooting stars.
const MOTES = Array.from({ length: 10 }, (_, i) => ({ x: 6 + ((i * 41) % 88), delay: -((i * 2.3) % 18), duration: 14 + (i % 4) * 3, size: 2 + (i % 3) }))
const CAPTIONS = ['Map your skills from your CV', 'See careers that fit you', 'Understand how you like to work', 'Get a step-by-step roadmap']
const HEADLINE = [['A', 'clearer', 'path.'], ['A', 'brighter', 'future.']]

// A fixed, deterministic star field (no random numbers at render time).
const STARS = Array.from({ length: 46 }, (_, i) => ({
  x: (i * 37.7) % 100, y: (i * 61.3 + (i % 7) * 9) % 100,
  size: 1 + (i % 3) * 0.6, delay: -((i * 0.73) % 6), duration: 3 + (i % 5),
}))

// Runs `tick` on an interval only while the tab is visible.
function useVisibleInterval(tick, ms, enabled = true) {
  useEffect(() => {
    if (!enabled) return undefined
    let timer = null
    const start = () => { if (!timer && !document.hidden) timer = setInterval(tick, ms) }
    const stop = () => { clearInterval(timer); timer = null }
    const onVisibility = () => (document.hidden ? stop() : start())
    start()
    document.addEventListener('visibilitychange', onVisibility)
    return () => { stop(); document.removeEventListener('visibilitychange', onVisibility) }
  }, [tick, ms, enabled])
}

const fade = (delay, y = 12) => ({ initial: { opacity: 0, y }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.6, ease: EASE, delay } })

export default function BrandPanel() {
  const reduced = useReducedMotion()
  const panel = useRef(null)
  const frame = useRef(0)
  const [active, setActive] = useState(0)
  const [caption, setCaption] = useState(0)
  useVisibleInterval(() => setActive(value => (value + 1) % STEPS.length), 4000)
  useVisibleInterval(() => setCaption(value => (value + 1) % CAPTIONS.length), 5000)

  // Pointer parallax: layers read --px/--py (-1..1) and shift a few px at different depths.
  function onPointerMove(event) {
    if (reduced || event.pointerType === 'touch') return
    const { clientX, clientY } = event
    cancelAnimationFrame(frame.current)
    frame.current = requestAnimationFrame(() => {
      const box = panel.current?.getBoundingClientRect()
      if (!box) return
      panel.current.style.setProperty('--px', (((clientX - box.left) / box.width) * 2 - 1).toFixed(3))
      panel.current.style.setProperty('--py', (((clientY - box.top) / box.height) * 2 - 1).toFixed(3))
    })
  }
  useEffect(() => () => cancelAnimationFrame(frame.current), [])

  let wordIndex = 0
  return <section ref={panel} className="ab-panel" aria-label="Welcome to CareerNova" onPointerMove={onPointerMove}
    onPointerLeave={() => { panel.current?.style.setProperty('--px', 0); panel.current?.style.setProperty('--py', 0) }}>
    <div className="ab-sky" aria-hidden="true">
      <div className="ab-layer ab-depth-1">{STARS.map((star, i) => <i key={i} className="ab-star" style={{ left: `${star.x}%`, top: `${star.y}%`, '--s': `${star.size}px`, animationDelay: `${star.delay}s`, animationDuration: `${star.duration}s` }} />)}</div>
      <div className="ab-layer ab-depth-1"><i className="ab-shoot ab-shoot-1" /><i className="ab-shoot ab-shoot-2" /><i className="ab-shoot ab-shoot-3" /></div>
      <div className="ab-layer ab-depth-2"><span className="ab-blob ab-blob-1" /><span className="ab-blob ab-blob-2" /><span className="ab-blob ab-blob-3" />
        {MOTES.map((mote, i) => <i key={i} className="ab-mote" style={{ left: `${mote.x}%`, '--m': `${mote.size}px`, animationDelay: `${mote.delay}s`, animationDuration: `${mote.duration}s` }} />)}</div>
    </div>

    <m.div {...fade(0, 0)} initial={{ opacity: 0, x: -14 }} animate={{ opacity: 1, x: 0 }}>
      <Link to="/login" className="brand ab-brand"><span className="brand-mark"><Icon size={27} /></span><span>CareerNova<small>CAREER INTELLIGENCE</small></span></Link>
    </m.div>

    <div className="ab-copy">
      <m.p className="ab-kicker" {...fade(0.25, 6)}><span className="ab-kicker-dot" aria-hidden="true" /> YOUR POTENTIAL. YOUR POSSIBILITIES.</m.p>
      <h1 aria-label="A clearer path. A brighter future.">
        {HEADLINE.map((line, row) => <span key={row} className="ab-line" aria-hidden="true">{line.map(word => {
          const delay = 0.45 + (wordIndex++) * 0.08
          return <span key={word} className="ab-word"><m.span className={word === 'future.' ? 'ab-shimmer' : undefined}
            initial={{ y: '110%' }} animate={{ y: '0%' }} transition={{ duration: 0.7, ease: EASE, delay }}>{word}</m.span></span>
        })}</span>)}
      </h1>
      <m.p className="ab-sub" {...fade(1.05)}>Connect your skills, discover your strengths, and find a career direction that feels like you.</m.p>
      <m.div className="ab-caption" {...fade(1.25, 0)} aria-hidden="true">
        <Icon name="spark" size={13} />
        <AnimatePresence mode="wait" initial={false}>
          <m.span key={caption} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.35, ease: EASE }}>{CAPTIONS[caption]}</m.span>
        </AnimatePresence>
      </m.div>
    </div>

    <m.div className="ab-universe" aria-hidden="true" initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.9, ease: EASE, delay: 0.8 }}>
      <div className="ab-layer ab-depth-3">
        <div className="ab-orbit">
          <div className="ab-ring ab-ring-dashed"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="49" /></svg></div>
          <div className="ab-ring ab-ring-3"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="49" /></svg></div>
          <div className="ab-ring ab-ring-2"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="49" /></svg></div>
          <div className="ab-ring ab-ring-1"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="49" /></svg></div>
          {STEPS.map((step, index) => <div key={step.key} className={`ab-node-track ab-track-${index} ${index === active ? 'is-active' : ''}`}>
            <span className="ab-node"><span className="ab-node-label"><span>{step.label}</span></span></span>
          </div>)}
          {!reduced && <span key={active} className="ab-ripple" />}
          <div className="ab-core"><span className="ab-core-glow" /><span className="ab-core-sweep" /><Icon size={52} /><span>Your next chapter</span><small>STARTS WITH YOU</small></div>
        </div>
        <svg className="ab-links" viewBox="0 0 100 100" preserveAspectRatio="none">
          {STEPS.map((step, index) => <path key={step.key} d={step.line} pathLength="1" className={index === active ? 'is-active' : ''} vectorEffect="non-scaling-stroke" />)}
          {!reduced && <circle key={active} className="ab-spark" r="0.7"><animateMotion dur="1.8s" repeatCount="indefinite" path={STEPS[active].line} /></circle>}
        </svg>
        {STEPS.map((step, index) => <FloatCard key={step.key} step={step} active={index === active} index={index} reduced={reduced} />)}
      </div>
    </m.div>

    <m.div className="ab-footer" {...fade(1.4, 6)}>
      <span className="ab-footer-line" aria-hidden="true" />
      <p>Built for the journey ahead.<small>An AI-powered career research experience.</small></p>
    </m.div>
  </section>
}

// A floating step card: bobs gently, tilts toward the pointer (max 6°), glows when active.
function FloatCard({ step, active, index, reduced }) {
  const tilt = useRef(null)
  function onMove(event) {
    if (reduced || !tilt.current) return
    const box = tilt.current.getBoundingClientRect()
    tilt.current.style.setProperty('--ry', `${(((event.clientX - box.left) / box.width) - 0.5) * 12}deg`)
    tilt.current.style.setProperty('--rx', `${(0.5 - ((event.clientY - box.top) / box.height)) * 12}deg`)
  }
  const reset = () => { tilt.current?.style.setProperty('--rx', '0deg'); tilt.current?.style.setProperty('--ry', '0deg') }
  return <div className={`ab-card-spot ab-spot-${step.spot}`}>
    <div ref={tilt} className={`ab-card ${active ? 'is-active' : ''}`} onPointerMove={onMove} onPointerLeave={reset} style={{ '--bob-delay': `${-index * 1.5}s` }}>
      <div className="ab-card-body"><span className={`ab-card-icon ab-icon-${step.key}`}><Icon name={step.icon} /></span>
        <div><b>{step.title}</b><small>{step.note}</small></div><em className="ab-card-step">0{index + 1}</em></div>
      {active && !reduced && <span className="ab-card-progress" aria-hidden="true" />}
    </div>
  </div>
}
