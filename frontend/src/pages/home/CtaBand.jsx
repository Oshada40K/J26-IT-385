// Closing call to action: upload a CV, or continue with the next real step of the journey.
import { Link } from 'react-router-dom'
import Icon from '../../components/Icon.jsx'
import { nextStep } from './journeyStatus.js'
import { Reveal } from './MotionRoot.jsx'

export default function CtaBand({ journey, onUpload }) {
  const hasCv = journey.loaded && journey.statuses.c01 === 'done'
  const next = hasCv ? nextStep(journey.statuses) : null
  return <Reveal as="section" className="cta-band" aria-labelledby="cta-title">
    <div>
      <h2 id="cta-title">Ready to see where you fit?</h2>
      <p>{hasCv ? (next ? `Next up: ${next.label.toLowerCase()}.` : 'All four steps are complete. Review your results any time.') : 'Upload your CV to get your skill profile, career matches and a learning roadmap.'}</p>
    </div>
    <div className="cta-actions">
      {hasCv
        ? <Link className="button cta-primary" to={next ? next.to : '/component03'}>{next ? 'Continue your journey' : 'Review your career matches'}<Icon name="arrow" size={17} /></Link>
        : <button type="button" className="cta-primary" onClick={onUpload}><Icon name="upload" size={17} />Upload your CV</button>}
      <Link className="button cta-secondary" to="/component03">Explore careers</Link>
    </div>
  </Reveal>
}
