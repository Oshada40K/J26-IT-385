// Owner: Dewmi - Component 04: explainable results for a Career Readiness Assessment.
// Shows the readiness score, confidence-aware skill gaps, priorities and the staged learning roadmap.
import { useEffect, useState } from 'react'
import Icon from '../../components/Icon.jsx'
import { getAnalysis } from './assessmentApi.js'
import './RoadmapResults.css'

const STATUS = {
  gap: { label: 'Gap', className: 'is-gap' },
  review: { label: 'Review', className: 'is-review' },
  met: { label: 'Met', className: 'is-met' },
  prerequisite: { label: 'Prerequisite', className: 'is-prereq' },
}
const FACTOR_CLASS = ['f1', 'f2', 'f3', 'f4', 'f5']
const formatDate = value => value ? new Date(value).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : '—'
const signed = value => `${value >= 0 ? '+' : '−'}${Math.abs(value).toFixed(1)}`

function formatValue(term) {
  if (term.unit === 'percent') return `${Math.round(term.value * 100)}%`
  if (term.unit === 'number') return term.value.toFixed(1)
  return String(Math.round(term.value))
}

function LevelBar({ current, required }) {
  return <div className="c4r-level" aria-label={`CV evidence level ${current} of 5; required level ${required} of 5`}>
    {[1, 2, 3, 4, 5].map(level => <span key={level} className={`${level <= current ? 'filled' : ''} ${level === required ? 'target' : ''}`} />)}
  </div>
}

function ScoreRing({ score }) {
  const radius = 52
  const circumference = 2 * Math.PI * radius
  return <svg className="c4r-ring" viewBox="0 0 128 128" role="img" aria-label={`Readiness score ${Math.round(score)} out of 100`}>
    <circle cx="64" cy="64" r={radius} className="c4r-ring-track" />
    <circle cx="64" cy="64" r={radius} className="c4r-ring-value" strokeDasharray={circumference}
      strokeDashoffset={circumference * (1 - score / 100)} transform="rotate(-90 64 64)" />
    <text x="64" y="62" textAnchor="middle" className="c4r-ring-score">{Math.round(score)}</text>
    <text x="64" y="82" textAnchor="middle" className="c4r-ring-max">/ 100</text>
  </svg>
}

function Readiness({ readiness, assessment }) {
  const previous = assessment.previous?.readiness_score
  return <section className="card c4r-section" aria-labelledby="c4r-readiness">
    <div className="c4r-section-title"><span className="step-number">01</span><h2 id="c4r-readiness">Career readiness score</h2></div>
    <div className="c4r-readiness">
      <div className="c4r-score">
        <ScoreRing score={readiness.score} />
        <span className={`c4r-band band-${readiness.band.toLowerCase().replace(/\s+/g, '-')}`}>{readiness.band}</span>
        {previous != null && <small className="c4r-delta">{signed(readiness.score - previous)} since your previous assessment</small>}
      </div>
      <div className="c4r-readiness-text">
        <p className="c4r-summary">{readiness.summary}</p>
        <p className="c4r-caution"><Icon name="spark" size={15} />This score summarises the evidence available for this career. It is not a probability of getting a job.</p>
        <details className="c4r-breakdown">
          <summary>How this score was calculated</summary>
          <p className="muted">{readiness.formula}</p>
          <div className="table-scroll"><table>
            <thead><tr><th>Factor</th><th>Your value</th><th>Coefficient</th><th>Points</th></tr></thead>
            <tbody>
              <tr><td>Model intercept (starting value)</td><td>—</td><td>—</td><td className="c4r-points">{signed(readiness.intercept)}</td></tr>
              {readiness.groups.map(group => [
                <tr key={group.name} className="c4r-group-row"><td colSpan={3}>{group.name}</td><td className="c4r-points">{signed(group.points)}</td></tr>,
                ...group.terms.map(term => <tr key={term.feature}>
                  <td>{term.label}</td><td>{formatValue(term)}</td><td>{term.coefficient.toFixed(2)}</td>
                  <td className={`c4r-points ${term.points >= 0 ? 'is-positive' : 'is-negative'}`}>{signed(term.points)}</td>
                </tr>),
              ])}
              <tr className="c4r-total-row"><td colSpan={3}>Total (limited to 0–100)</td><td className="c4r-points">{readiness.score.toFixed(1)}</td></tr>
            </tbody>
          </table></div>
          <p className="muted">Bands: {readiness.bands.map(b => `${b.band} ${b.range}`).join(' · ')}</p>
        </details>
      </div>
    </div>
  </section>
}

function SkillGaps({ gaps }) {
  const { summary, skills } = gaps
  return <section className="card c4r-section" aria-labelledby="c4r-gaps">
    <div className="c4r-section-title"><span className="step-number">02</span><h2 id="c4r-gaps">Skill gap analysis</h2></div>
    <p className="muted">Your CV evidence (Component 01) compared with the O*NET requirements for this career. Self-ratings are shown alongside but never count as proficiency.</p>
    <div className="c4r-stats">
      <div><strong>{summary.gaps}</strong><span>Gaps ({summary.critical} critical)</span></div>
      <div><strong>{summary.review}</strong><span>To review</span></div>
      <div><strong>{summary.met}</strong><span>Met</span></div>
      <div><strong>{summary.required}</strong><span>Required skills</span></div>
    </div>
    <div className="c4r-skill-list">
      {skills.map(skill => <article key={skill.skill_id} className={`c4r-skill ${STATUS[skill.status].className}`}>
        <div className="c4r-skill-head">
          <div>
            <h3>{skill.skill_name}</h3>
            <div className="c4r-tags">
              <span className={`c4r-status ${STATUS[skill.status].className}`}>{STATUS[skill.status].label}{skill.status === 'gap' ? ` · ${skill.severity}` : ''}</span>
              {skill.is_essential && <span className="c4r-tag">Essential</span>}
              {skill.hot_technology && <span className="c4r-tag">O*NET Hot Technology</span>}
              {skill.priority_rank && <span className="c4r-tag">Priority #{skill.priority_rank}</span>}
            </div>
          </div>
        </div>
        <dl className="c4r-skill-facts">
          <div><dt>CV evidence</dt><dd><LevelBar current={skill.current_level} required={skill.required_level} /><small>{skill.current_level}/5 · needed {skill.required_level}/5</small></dd></div>
          <div><dt>Your confidence</dt><dd>{skill.not_studied ? 'Not studied' : skill.self_rating == null ? 'Not rated' : `${skill.self_rating}/5`}</dd></div>
          <div><dt>Evidence source</dt><dd>{skill.evidence_source === 'none' ? 'Not found in CV' : `${skill.evidence_source}${skill.evidence_strength ? ` (${skill.evidence_strength})` : ''}`}</dd></div>
        </dl>
        {skill.notes.filter(n => !n.startsWith('No self-rating')).map(note => <p key={note} className="c4r-note">{note}</p>)}
      </article>)}
    </div>
  </section>
}

function Priorities({ priorities, method }) {
  if (!priorities.length) return null
  return <section className="card c4r-section" aria-labelledby="c4r-priorities">
    <div className="c4r-section-title"><span className="step-number">03</span><h2 id="c4r-priorities">Skill priorities</h2></div>
    <p className="muted">Each gap is ranked by a transparent weighted score. The coloured bar shows how much each factor contributed.</p>
    <ul className="c4r-legend" aria-label="Priority factors">
      {method.priority_factors.map((f, i) => <li key={f.key}><span className={`c4r-swatch ${FACTOR_CLASS[i]}`} />{f.label} <small>(weight {f.weight.toFixed(2)})</small></li>)}
    </ul>
    <ol className="c4r-priorities">
      {priorities.map(p => <li key={p.skill_id}>
        <span className="rank-badge">{p.rank}</span>
        <div className="c4r-priority-body">
          <div className="c4r-priority-head"><strong>{p.skill_name}</strong><span>{p.priority_score.toFixed(2)}</span></div>
          <div className="c4r-stack" role="img" aria-label={p.factors.map(f => `${f.label} ${f.points.toFixed(2)}`).join(', ')}>
            {p.factors.map((f, i) => <span key={f.key} className={FACTOR_CLASS[i]} style={{ width: `${f.points * 100}%` }} />)}
          </div>
          <small className="muted">{p.why}</small>
        </div>
      </li>)}
    </ol>
    <details className="c4r-breakdown">
      <summary>Scoring formula</summary>
      <p><code className="c4r-formula">{method.priority_formula}</code></p>
      <ul>{method.priority_factors.map(f => <li key={f.key}><strong>{f.label}:</strong> {f.definition}.</li>)}</ul>
      <p className="muted">{method.priority_weights_source}</p>
    </details>
  </section>
}

function Resource({ resource }) {
  return <li className="c4r-resource">
    <a href={resource.url} target="_blank" rel="noopener noreferrer">{resource.title} <Icon name="arrow" size={13} /></a>
    <small>{[resource.type, resource.level, resource.duration_hours ? `${resource.duration_hours} h` : null, resource.is_free ? 'Free' : null].filter(Boolean).join(' · ')}</small>
    <small className="muted">{resource.why}</small>
  </li>
}

function RoadmapStep({ step }) {
  return <details className="c4r-step">
    <summary>
      <span className="c4r-step-number">{step.step}</span>
      <span className="c4r-step-title"><strong>{step.skill_name}</strong><small>{step.reason}</small></span>
      <span className="c4r-step-meta"><span className={`c4r-status ${STATUS[step.status].className}`}>{STATUS[step.status].label}</span><small>Weeks {step.start_week}–{step.end_week} · {step.estimated_hours} h</small></span>
    </summary>
    <div className="c4r-step-body">
      {step.prerequisites.length > 0 && <p className="muted">Builds on: {step.prerequisites.join(', ')}</p>}
      <div className="c4r-step-grid">
        <div><h4>Learning activities</h4><ul>{step.activities.map(a => <li key={a}>{a}</li>)}</ul></div>
        <div><h4>Practical project</h4><p>{step.project}</p></div>
        <div><h4>Milestones</h4><ul className="c4r-milestones">{step.milestones.map(m => <li key={m}><Icon name="check" size={14} />{m}</li>)}</ul></div>
        <div><h4>Recommended resources</h4>{step.resources.length ? <ul className="c4r-resources">{step.resources.map(r => <Resource key={r.resource_id} resource={r} />)}</ul> : <p className="muted">No resources are available for this skill in the current dataset.</p>}</div>
      </div>
    </div>
  </details>
}

function Roadmap({ roadmap }) {
  return <section className="card c4r-section" aria-labelledby="c4r-roadmap">
    <div className="c4r-section-title"><span className="step-number">04</span><h2 id="c4r-roadmap">Personalised learning roadmap</h2></div>
    {roadmap.total_steps === 0 ? <p>Your CV evidence already meets every requirement for this career. Keep your skills current and add new evidence to your CV.</p> : <>
      <div className="c4r-stats">
        <div><strong>{roadmap.total_steps}</strong><span>Skills to develop</span></div>
        <div><strong>{Math.round(roadmap.total_hours)}</strong><span>Estimated hours</span></div>
        <div><strong>{roadmap.total_weeks}</strong><span>Weeks at {roadmap.weekly_hours} h/week</span></div>
      </div>
      <p className="muted">Prerequisites come first. Durations are planning estimates; select a step to see activities, a project, milestones and resources.</p>
      <div className="c4r-stages">
        {roadmap.stages.map(stage => <div key={stage.stage} className={`c4r-stage stage-${stage.stage.toLowerCase()}`}>
          <div className="c4r-stage-head">
            <h3>{stage.stage}</h3>
            <small>Weeks {stage.start_week}–{stage.end_week} · {Math.round(stage.estimated_hours)} h</small>
          </div>
          <p className="c4r-stage-milestone"><Icon name="check" size={15} />{stage.milestone}</p>
          {stage.steps.map(step => <RoadmapStep key={step.step} step={step} />)}
        </div>)}
      </div>
    </>}
  </section>
}

function Method({ result }) {
  const { method, model_info: model } = result
  return <details className="card c4r-method">
    <summary>Method, data sources and limitations</summary>
    <h3>Skill gap analysis</h3><p>{method.gap_analysis}</p>
    <h3>Resources and roadmap</h3><p>{method.resource_ranking}</p><p>{method.roadmap_ordering}</p>
    <h3>Data sources</h3><ul>{method.data_sources.map(s => <li key={s}>{s}</li>)}</ul>
    <h3>Limitations</h3><ul>{method.limitations.map(s => <li key={s}>{s}</li>)}</ul>
    <p className="muted">Models: {model.gap_model} (skill gap), {model.readiness_model} (readiness) · C4 {model.versions?.c4} · trained {model.versions?.trained_at} on {model.versions?.training_data} · O*NET {model.versions?.onet}</p>
  </details>
}

export default function RoadmapResults({ assessmentId, onEdit, onNew }) {
  const [state, setState] = useState({ loading: true, error: '', result: null })
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let active = true
    setState({ loading: true, error: '', result: null })
    getAnalysis(assessmentId)
      .then(result => { if (active) setState({ loading: false, error: '', result }) })
      .catch(error => { if (active) setState({ loading: false, error: error.message, result: null }) })
    return () => { active = false }
  }, [assessmentId, reload])

  if (state.loading) return <div className="card" role="status">Analysing your skills and building your roadmap…</div>
  if (state.error) return <div className="card c4r-error">
    <p className="error-message" role="alert">{state.error}</p>
    <div className="c4r-actions"><button type="button" onClick={() => setReload(v => v + 1)}>Try again</button><button type="button" className="button-secondary" onClick={onEdit}>Edit my assessment</button></div>
  </div>

  const { result } = state
  const { assessment } = result
  return <div className="c4r">
    <section className="card c4r-overview">
      <div>
        <p className="eyebrow">TARGET CAREER</p>
        <h2>{result.target_career.career_name}</h2>
        <p className="muted">Assessment submitted {formatDate(assessment.submitted_at)} · CV assessed {formatDate(assessment.cv_assessed_at)}</p>
      </div>
      <div className="c4r-actions">
        <button type="button" onClick={onEdit}>Update my assessment</button>
        <button type="button" className="button-secondary" onClick={onNew}>Choose another career</button>
      </div>
      {[...assessment.changes, ...result.warnings].map(message => <p key={message} className="c4r-notice" role="status">{message}</p>)}
      {result.inputs.cv_skills_not_in_catalogue.length > 0 && <p className="c4r-notice">CV skills not covered by the C4 skills catalogue (not used): {result.inputs.cv_skills_not_in_catalogue.join(', ')}.</p>}
    </section>
    <Readiness readiness={result.readiness} assessment={assessment} />
    <SkillGaps gaps={result.skill_gaps} />
    <Priorities priorities={result.priorities} method={result.method} />
    <Roadmap roadmap={result.roadmap} />
    {assessment.history.length > 1 && <section className="card c4r-section" aria-labelledby="c4r-history">
      <h2 id="c4r-history">Assessment history</h2>
      <div className="table-scroll"><table className="c4r-history">
        <thead><tr><th>Submitted</th><th>Career</th><th>Readiness at submission</th></tr></thead>
        <tbody>{assessment.history.map(h => <tr key={h.assessment_id} className={h.assessment_id === assessment.assessment_id ? 'is-current' : ''}>
          <td>{formatDate(h.submitted_at)}</td><td>{h.career_name}</td><td>{h.readiness_score == null ? '—' : Math.round(h.readiness_score)}</td>
        </tr>)}</tbody>
      </table></div>
    </section>}
    <Method result={result} />
  </div>
}
