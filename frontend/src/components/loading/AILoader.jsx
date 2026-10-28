// Shared AI loading visuals: an animated "intelligence core" with orbit rings and particles,
// cycling status messages, optional pipeline steps, and a page-level loader with skeletons.
// Screen readers get one stable label (role="status"); the cycling text is decorative.
import { useEffect, useState } from 'react'
import Icon from '../Icon.jsx'
import './loading.css'

export const LOADING_MESSAGES = {
  skills: ['Analyzing Your Skills…', 'Reading the evidence in your CV…', 'Estimating your skill levels…'],
  personality: ['Evaluating Your Personality…', 'Combining your answers, choices and writing…', 'Checking consistency across your sources…'],
  career: ['Finding the Best Career Matches…', 'Comparing your profile with O*NET occupations…', 'Explaining your match with SHAP…'],
  roadmap: ['Generating Your Learning Roadmap…', 'Measuring your skill gaps…', 'Ordering prerequisites into stages…'],
  workspace: ['Opening Your Workspace…', 'Restoring your secure session…', 'Preparing your career intelligence…'],
}

const VARIANTS = {
  skills: { icon: 'skill', eyebrow: 'C01 · SKILL ASSESSMENT' },
  personality: { icon: 'personality', eyebrow: 'C02 · PERSONALITY PROFILE' },
  career: { icon: 'career', eyebrow: 'C03 · CAREER MATCHING' },
  roadmap: { icon: 'roadmap', eyebrow: 'C04 · LEARNING ROADMAP' },
  workspace: { icon: 'spark', eyebrow: 'CAREERNOVA AI' },
}

const SLOW_AFTER_MS = 12000

// Fixed pseudo-random layout so particles do not jump between renders.
const particles = count => Array.from({ length: count }, (_, i) => ({
  '--x': `${(i * 37 + 11) % 100}%`,
  '--y': `${(i * 53 + 23) % 100}%`,
  '--d': `${((i * 0.73) % 5).toFixed(2)}s`,
  '--t': `${5 + (i % 4) * 1.4}s`,
  '--s': `${2 + (i % 3)}px`,
}))
const ORB_PARTICLES = particles(10)
const FIELD_PARTICLES = particles(26)

function useCycle(length, interval = 2600) {
  const [index, setIndex] = useState(0)
  useEffect(() => {
    setIndex(0)
    if (length < 2) return undefined
    const id = setInterval(() => setIndex(i => (i + 1) % length), interval)
    return () => clearInterval(id)
  }, [length, interval])
  return length ? index % length : 0
}

function useDelay(ms) {
  const [ready, setReady] = useState(ms <= 0)
  useEffect(() => {
    if (ms <= 0) return undefined
    const id = setTimeout(() => setReady(true), ms)
    return () => clearTimeout(id)
  }, [ms])
  return ready
}

function useElapsed(ms) {
  const [passed, setPassed] = useState(false)
  useEffect(() => {
    const id = setTimeout(() => setPassed(true), ms)
    return () => clearTimeout(id)
  }, [ms])
  return passed
}

function Orb({ icon, withParticles }) {
  return <div className="ai-orb" aria-hidden="true">
    <span className="ai-orb-glow" />
    <span className="ai-orb-ring ai-orb-ring-arc" />
    <span className="ai-orb-ring ai-orb-ring-dash" />
    <span className="ai-orb-ring ai-orb-ring-ping" />
    <span className="ai-orb-core"><Icon name={icon} size={26} /></span>
    {withParticles && <span className="ai-particles">{ORB_PARTICLES.map((style, i) => <i key={i} style={style} />)}</span>}
  </div>
}

/**
 * variant: skills | personality | career | roadmap | workspace
 * size: sm | md | lg       mode: inline (default) | overlay | fullscreen
 * steps: [{ label, messages }] with activeStep, for multi-stage pipelines.
 * delay: ms before anything renders, so quick operations never show the loader.
 */
export function AILoader({ variant = 'career', messages, steps, activeStep = 0, label, size = 'md', mode = 'inline', delay = 0, className = '' }) {
  const config = VARIANTS[variant] || VARIANTS.career
  const step = steps?.[Math.min(activeStep, steps.length - 1)]
  const lines = step?.messages || messages || LOADING_MESSAGES[variant] || LOADING_MESSAGES.career
  const index = useCycle(lines.length)
  const slow = useElapsed(SLOW_AFTER_MS)
  const headline = step ? step.label : lines[index]
  const subline = step ? lines[index] : null
  const srLabel = label || step?.label || lines[0]
  const visible = useDelay(delay)
  if (!visible) return null

  return <div className={`ai-loader ai-loader-${size} ai-loader-${mode} ai-variant-${variant} ${className}`} role="status" aria-live="polite">
    <span className="sr-only">{srLabel}</span>
    {mode === 'fullscreen' && <span className="ai-particles ai-particle-field" aria-hidden="true">{FIELD_PARTICLES.map((style, i) => <i key={i} style={style} />)}</span>}
    <Orb icon={config.icon} withParticles={size !== 'sm'} />
    <div className="ai-loader-copy" aria-hidden="true">
      {size !== 'sm' && <span className="ai-loader-eyebrow">{config.eyebrow}</span>}
      <strong className="ai-loader-headline" key={headline}>{headline}</strong>
      {subline && <span className="ai-loader-subline" key={subline}>{subline}</span>}
      {steps && <ol className="ai-loader-steps">
        {steps.map((s, i) => <li key={s.label} className={i < activeStep ? 'is-done' : i === activeStep ? 'is-active' : ''}>
          <span className="ai-step-dot">{i < activeStep && <Icon name="check" size={11} />}</span>{s.label.replace(/…$/, '')}
        </li>)}
      </ol>}
      <span className="ai-loader-bar"><i /></span>
      {slow && <span className="ai-loader-slow">Still working. The first run can take up to a minute while the models load.</span>}
    </div>
  </div>
}

// Page-level loading state: AI banner plus a skeleton of the content that is coming.
// It fades in after a short delay, so fast responses never flash a loader.
export function PageLoader({ variant, messages, label, skeleton, delay = 160 }) {
  return <div className="fx-delayed" style={{ '--fx-delay': `${delay}ms` }}>
    <AILoader variant={variant} messages={messages} label={label} />
    {skeleton}
  </div>
}
