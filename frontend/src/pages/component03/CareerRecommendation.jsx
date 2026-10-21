// Owner: Oshada - Component 03: Explainable Career Recommendation.
// Loads the three career APIs and presents them as one result view. The backend
// builds the recommendation from the Component 01 and 02 profiles for the saved candidate.
// Page sections: best-job hero + score ring, "Why this career?" reasons, SHAP factor
// chart, matched skills / skills to learn (-> Component 04), top 5 jobs, model summary.
import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { API_BASE_URL } from '../../api/client.js'
import { savedSession } from '../component01/skillApi.js'
import { ENDPOINTS, describeCareerError, getCareerResult } from './careerApi.js'
import './CareerRecommendation.css'

function ScoreRing({ score }) {
  const radius = 64
  const circumference = 2 * Math.PI * radius
  const [shown, setShown] = useState(0)
  useEffect(() => { const id = requestAnimationFrame(() => setShown(score)); return () => cancelAnimationFrame(id) }, [score])
  return (
    <div className="c3-ring" role="img" aria-label={`Match score ${Math.round(score)} out of 100`}>
      <svg width="100%" height="100%" viewBox="0 0 150 150">
        <circle className="c3-ring-track" cx="75" cy="75" r={radius} fill="none" strokeWidth="12" />
        <circle className="c3-ring-fill" cx="75" cy="75" r={radius} fill="none" strokeWidth="12"
          strokeDasharray={circumference} strokeDashoffset={circumference * (1 - shown / 100)} />
      </svg>
      <div className="c3-ring-value">
        <strong>{Math.round(score)}</strong>
        <small>MATCH / 100</small>
      </div>
    </div>
  )
}

function Hero({ title, score, occupations, matchedCount }) {
  return (
    <section className="c3-hero">
      <div>
        <div className="c3-hero-label">★ YOUR BEST CAREER MATCH</div>
        <h2>{title}</h2>
        <p>Ranked first out of {occupations} occupations by comparing your CV skills and soft skills with O*NET job requirements.</p>
        <div className="c3-hero-meta">
          {matchedCount > 0 && <span>{matchedCount} of your skills used in this job</span>}
          <span>Explained with SHAP</span>
        </div>
      </div>
      {score != null && <ScoreRing score={score} />}
    </section>
  )
}

function WhyCard({ reasons }) {
  return (
    <div className="c3-card">
      <h3>Why this career?</h3>
      <p className="c3-card-sub">The main reasons behind your recommendation</p>
      <ul className="c3-reasons">
        {reasons.map((reason) => {
          const down = reason.startsWith('What lowered')
          return (
            <li key={reason}>
              <span className={`c3-reason-icon ${down ? 'down' : ''}`}>{down ? '−' : '✓'}</span>
              <span>{reason}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function FactorChart({ factors, shapText }) {
  const max = Math.max(...factors.map((f) => Math.abs(f.points)), 1)
  return (
    <div className="c3-card">
      <h3>What shaped your score</h3>
      <p className="c3-card-sub">Each factor's effect on the match score, in points</p>
      {factors.map((f) => (
        <div className="c3-factor" key={`${f.effect}-${f.label}`}>
          <span className="c3-factor-label" title={f.label}>{f.label}</span>
          <div className="c3-factor-track">
            <div className={`c3-factor-bar ${f.effect}`} style={{ width: `${Math.max((Math.abs(f.points) / max) * 100, 2)}%` }} />
          </div>
          <span className={`c3-factor-points ${f.effect}`}>{f.points > 0 ? '+' : ''}{f.points.toFixed(1)}</span>
        </div>
      ))}
      <div className="c3-legend"><span><i />Raised the score</span><span><i className="negative" />Lowered the score</span></div>
      <details className="c3-details">
        <summary>Technical details (SHAP)</summary>
        <ul>{shapText.map((s) => <li key={s}>{s}</li>)}</ul>
      </details>
    </div>
  )
}

function SkillsCard({ title, subtitle, skills, kind, children }) {
  return (
    <div className="c3-card">
      <h3>{title}</h3>
      <p className="c3-card-sub">{subtitle}</p>
      {skills.length ? (
        <div className="c3-chips">{skills.map((s) => <span key={s} className={`c3-chip ${kind}`}>{s}</span>)}</div>
      ) : <p className="muted" style={{ margin: 0 }}>None found.</p>}
      {children}
    </div>
  )
}

function TopJobs({ jobs }) {
  return (
    <div className="c3-card c3-full">
      <h3>Your top 5 career matches</h3>
      <p className="c3-card-sub">Alternatives worth exploring, ranked by match score</p>
      <div className="c3-jobs">
        {jobs.map((job) => (
          <div key={job.ranking} className={`c3-job ${job.ranking === 1 ? 'best' : ''}`}>
            <span className="c3-rank">{job.ranking}</span>
            <span className="c3-job-title">
              {job.job}
              <span className="c3-job-tag">{job.ranking === 1 ? 'Best match' : `Alternative ${job.ranking - 1}`}</span>
            </span>
            <div className="c3-bar"><div style={{ width: `${job.score}%` }} /></div>
            <span className="c3-job-score">{job.score.toFixed(1)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ModelCard({ data }) {
  return (
    <div className="c3-card c3-full">
      <h3>How this recommendation works</h3>
      <p className="c3-card-sub">{data.score_meaning}.</p>
      <div className="c3-stats">
        <div className="c3-stat"><small>Model</small><strong>XGBoost + SHAP</strong></div>
        <div className="c3-stat"><small>Job data</small><strong>O*NET {data.onet_version}</strong></div>
        <div className="c3-stat"><small>Occupations compared</small><strong>{data.eligible_occupations}</strong></div>
        <div className="c3-stat"><small>Features per job</small><strong>21</strong></div>
      </div>
      <div className="c3-pipeline">
        <span>CV skills (C01)</span><b>+</b><span>Soft skills (C02)</span><b>→</b>
        <span>21 match features × {data.eligible_occupations} jobs</span><b>→</b>
        <span>XGBoost score</span><b>→</b><span>SHAP explanation</span>
      </div>
    </div>
  )
}

const emptyState = { loading: false, data: null, error: null }

export default function CareerRecommendation() {
  const location = useLocation()
  const [results, setResults] = useState(() => {
    const prediction = location.state
    return prediction?.candidateId === savedSession()?.candidate_id && prediction?.careerResults
      ? prediction.careerResults
      : { bestJob: emptyState, topJobs: emptyState, explanation: emptyState }
  })

  async function load(key) {
    setResults((prev) => ({ ...prev, [key]: { ...prev[key], loading: true, error: null } }))
    try {
      const data = await getCareerResult(key, API_BASE_URL, savedSession())
      setResults((prev) => ({ ...prev, [key]: { loading: false, data, error: null } }))
    } catch (err) {
      setResults((prev) => ({ ...prev, [key]: { loading: false, data: null, error: describeCareerError(err, API_BASE_URL) } }))
    }
  }

  const loadAll = () => Promise.all(Object.keys(ENDPOINTS).map(load))
  const states = Object.values(results)
  const anyLoading = states.some((r) => r.loading)
  const errors = [...new Set(states.map((r) => r.error).filter(Boolean))]
  const nothingYet = states.every((r) => !r.data && !r.error && !r.loading)

  // Load automatically unless results were passed from the CV upload.
  useEffect(() => { if (nothingYet) loadAll() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const best = results.bestJob.data
  const top = results.topJobs.data
  const why = results.explanation.data
  const metadata = best || top || why
  const isSample = !savedSession()?.candidate_id

  return (
    <div className="page accent-career">
      <div className="c3-header">
        <div>
          <p className="eyebrow">COMPONENT 03 / EXPLAINABLE CAREER INTELLIGENCE</p>
          <h1>Find your direction. Understand why.</h1>
          <p className="page-description">Your strongest career match, five ranked possibilities, and the evidence behind the recommendation.</p>
          <span className={`c3-pill ${isSample ? 'sample' : ''}`}>
            {isSample ? 'Sample profile: upload your CV in Skill assessment to personalise' : '● Based on your CV skills and personality profile'}
          </span>
        </div>
        <button className="button-secondary c3-refresh" onClick={loadAll} disabled={anyLoading}>
          {anyLoading ? 'Analysing…' : '↻ Refresh'}
        </button>
      </div>

      {errors.map((error) => (
        <div className="c3-error" role="alert" key={error}>
          <span>{error}</span>
          <button className="button-secondary" onClick={loadAll} disabled={anyLoading}>Try again</button>
        </div>
      ))}

      {anyLoading && !metadata && (
        <>
          <div className="c3-skeleton" style={{ height: 220 }} />
          <div className="c3-grid"><div className="c3-skeleton" style={{ height: 260, margin: 0 }} /><div className="c3-skeleton" style={{ height: 260, margin: 0 }} /></div>
        </>
      )}

      {(best || top) && (
        <Hero
          title={best?.best_job || top.jobs[0].job}
          score={why?.match_score ?? top?.jobs[0].score}
          occupations={metadata.eligible_occupations}
          matchedCount={why?.matched_technologies.length || 0}
        />
      )}

      {why && (
        <>
          <div className="c3-grid">
            <WhyCard reasons={why.key_reasons} />
            <FactorChart factors={why.factors} shapText={why.explanation.split(/(?<=\.)\s+/).filter(Boolean)} />
          </div>
          <div className="c3-grid">
            <SkillsCard title="Your matching skills" subtitle="Skills from your CV that this job uses" skills={why.matched_technologies} kind="have" />
            <SkillsCard title="Skills to learn next" subtitle="In-demand tools for this job that your CV doesn't show yet" skills={why.skills_to_learn} kind="learn">
              {why.skills_to_learn.length > 0 && (
                <p className="c3-note">Turn these into a step-by-step plan in your <Link to="/component04">Learning roadmap →</Link></p>
              )}
            </SkillsCard>
          </div>
        </>
      )}

      {top && <TopJobs jobs={top.jobs} />}

      {best?.unrecognised_skills?.length > 0 && (
        <p className="c3-note" style={{ marginTop: -8, marginBottom: 20 }}>
          Not used in matching (not in the O*NET skill catalogue): {best.unrecognised_skills.join(', ')}
        </p>
      )}

      {metadata && <ModelCard data={metadata} />}
    </div>
  )
}
