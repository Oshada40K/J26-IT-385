// Owner: Dewmi - Component 04: the target career decided by the system from Component 03's recommendation.
// Read-only: the student sees where the career came from (C03 rank, match score, C03's top 5) but cannot choose
// another career. Used by the assessment form and the results header.
import { Link } from 'react-router-dom'
import Icon from '../../components/Icon.jsx'

const formatScore = value => value == null ? '—' : Number(value).toFixed(1)

export function fallbackText(c3) {
  return c3?.fallback_used
    ? `Component 03's #1 is ${c3.c3_top1.job_title}, which is outside the IT roadmap, so your roadmap uses #${c3.c3_rank} ${c3.career_name}.`
    : ''
}

export function c3SourceText(c3) {
  return `Recommended by Component 03 — rank ${c3.c3_rank}, match score ${formatScore(c3.c3_score)}`
}

// Component 03's ranked jobs, read-only, with the career used for the roadmap highlighted.
export function C3TopJobs({ jobs, compact = false }) {
  return <ol className={`c4-c3-list ${compact ? 'is-compact' : ''}`} aria-label="Component 03's top 5 careers (read-only)">
    {jobs.map(job => <li key={job.rank} className={`c4-c3-job ${job.selected ? 'is-selected' : ''} ${job.supported ? '' : 'is-unsupported'}`}
      aria-current={job.selected ? 'true' : undefined}>
      <span className="rank-badge">{job.rank}</span>
      <span className="c4-match-text">
        <strong>{job.job_title}</strong>
        <small>Match score {formatScore(job.score)}{job.supported ? '' : ' · Not covered by the IT roadmap'}</small>
      </span>
      {job.selected && <span className="c4-c3-tag"><Icon name="check" size={14} />Your roadmap</span>}
    </li>)}
  </ol>
}

export default function C3CareerCard({ c3, cvSkillCount }) {
  return <section className="card c4-career" aria-labelledby="c4-career-title">
    <div className="c4-section-heading">
      <span className="component-icon"><Icon name="career" size={22} /></span>
      <div>
        <h2 id="c4-career-title">Your target career</h2>
        <p className="muted">Set by the system from Component 03's recommendation for your CV.</p>
      </div>
    </div>
    <p className="c4-c3-target">
      Your target career (recommended by Component 03): <strong>{c3.career_name}</strong> — rank {c3.c3_rank}, match score {formatScore(c3.c3_score)}
    </p>
    {c3.fallback_used && <p className="c4-c3-fallback" role="note"><Icon name="spark" size={15} />{fallbackText(c3)}</p>}
    <p className="c4-label">Component 03's top {c3.jobs.length} careers</p>
    <C3TopJobs jobs={c3.jobs} />
    <p className="c4-source-note">
      <Icon name="spark" size={15} />
      <span>
        {cvSkillCount
          ? `Skills are selected from the O*NET requirements for this career and the ${cvSkillCount} skills found in your CV.`
          : 'Skills are selected from the O*NET requirements for this career.'}
        {' '}To change your recommendation, update your CV in <Link to="/component01">Component 01</Link>.
      </span>
    </p>
  </section>
}

// Why the career could not be taken from Component 03, with a link to the component that can fix it.
export function C3CareerError({ error, onRetry }) {
  const needsCv = error?.status === 401 || error?.status === 409
  return <section className="card c4-career c4-c3-error" role="alert" aria-labelledby="c4-c3-error-title">
    <div className="c4-section-heading">
      <span className="component-icon"><Icon name="career" size={22} /></span>
      <div><h2 id="c4-c3-error-title">We could not set your target career</h2>
        <p className="muted">Your target career comes from Component 03's recommendation. It is never chosen by hand.</p></div>
    </div>
    <p>{error?.message || 'Component 03 did not return a recommendation.'}</p>
    <div className="c4-c3-actions">
      {needsCv
        ? <Link className="button" to="/component01">Go to Component 01 (upload your CV)</Link>
        : <Link className="button" to="/component03">Open Component 03</Link>}
      {onRetry && <button type="button" className="button-secondary" onClick={onRetry}>Try again</button>}
    </div>
  </section>
}
