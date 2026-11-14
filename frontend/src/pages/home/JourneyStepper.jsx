// "Your career journey": the four research components with their real status. The line fills
// up to the last completed step and the suggested next step pulses softly.
import { Link } from 'react-router-dom'
import Icon from '../../components/Icon.jsx'
import { STATUS_LABELS, STEPS, completedCount, nextStep } from './journeyStatus.js'
import { Reveal, RevealItem } from './MotionRoot.jsx'

export default function JourneyStepper({ journey, onStartHere }) {
  const { statuses, loaded } = journey
  const next = loaded ? nextStep(statuses) : null
  const done = completedCount(statuses)
  const lastDone = STEPS.reduce((last, step, index) => (statuses[step.key] === 'done' ? index : last), -1)
  const needsCv = loaded && statuses.c01 !== 'done'
  return <Reveal as="section" className="journey" aria-labelledby="journey-title">
    <header className="journey-head">
      <h2 id="journey-title">Your career journey</h2>
      <span className="journey-count">{loaded ? `${done} of ${STEPS.length} complete` : 'Checking your progress…'}</span>
    </header>
    {needsCv && <button type="button" className="start-here" onClick={onStartHere}>
      <span className="start-here-arrow" aria-hidden="true"><Icon name="arrow" size={15} /></span>
      Start here: upload your CV
    </button>}
    <div className="journey-track" style={{ '--fill': Math.max(lastDone, 0) / (STEPS.length - 1) }}>
    <span className="journey-line" aria-hidden="true"><i /></span>
    <ol className="journey-steps-list">
      {STEPS.map(step => {
        const status = loaded ? statuses[step.key] : 'checking'
        const isNext = next?.key === step.key
        return <RevealItem as="li" key={step.key} className={`journey-item is-${status} ${isNext ? 'is-next' : ''}`}>
          <Link to={step.to}>
            <span className="journey-node" aria-hidden="true">{status === 'done' ? <Icon name="check" size={16} /> : <Icon name={step.icon} size={16} />}</span>
            <span className="journey-text">
              <span className="journey-title"><small>{step.number}</small>{step.label}</span>
              <span className="journey-detail">{step.detail}</span>
            </span>
            <span className={`journey-status is-${status}`}><span className="sr-only">, </span>{status === 'checking' ? 'Checking…' : STATUS_LABELS[status]}{isNext && <span className="sr-only">, suggested next step</span>}</span>
          </Link>
        </RevealItem>
      })}
    </ol>
    </div>
  </Reveal>
}
