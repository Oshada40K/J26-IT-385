// Owner: Dewmi - Component 04: explainable results for a Career Readiness Assessment.
// Shows the readiness score, confidence-aware skill gaps, priorities and the staged learning roadmap.
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../../components/Icon.jsx'
import { deleteEvidence, getAnalysis, hasCvSession, listEvidence, recheckEvidence, submitEvidence } from './assessmentApi.js'
import './RoadmapResults.css'

const STATUS = {
  gap: { label: 'Gap', className: 'is-gap' },
  unverified: { label: 'Claimed – Not Verified', className: 'is-gap' },
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
        {readiness.potential_score != null && <p className="c4r-potential">Up to {readiness.potential_score}/100 if you verify: {readiness.potential_skills.join(', ')}</p>}
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

const PROOF_TYPES = [
  { value: 'github', label: 'GitHub repository', hint: 'https://github.com/<owner>/<repo> – a repository you own or contributed to' },
  { value: 'certificate_link', label: 'Certificate link', hint: 'For example a Credly, Coursera or Microsoft Learn link' },
  { value: 'certificate_file', label: 'Certificate file', hint: 'PDF, PNG or JPG, up to 5 MB' },
]
const MAX_PROOF_BYTES = 5 * 1024 * 1024

// Optional proof for a claimed skill. The roadmap never waits for it.
function ProofModal({ skill, onClose, onSubmitted }) {
  const [type, setType] = useState('github')
  const [url, setUrl] = useState('')
  const [file, setFile] = useState(null)
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const isFile = type === 'certificate_file'
  const id = `c4r-proof-${skill.skill_id}`

  useEffect(() => {
    const onKey = event => { if (event.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  async function handleSubmit(event) {
    event.preventDefault()
    if (isFile && !file) return setError('Choose a certificate file (PDF, PNG or JPG).')
    if (isFile && file.size > MAX_PROOF_BYTES) return setError('The file is larger than 5 MB.')
    if (!isFile && !/^https:\/\/\S+$/.test(url.trim())) return setError('The link must be a full https:// address.')
    setSaving(true)
    setError('')
    try {
      onSubmitted(await submitEvidence(skill.skill_id, type, isFile ? null : url.trim(), { file: isFile ? file : null, description: description.trim() }))
    } catch (err) {
      setError(err.message)                                  // validation messages from the API
      setSaving(false)
    }
  }

  return <div className="c4r-modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <div className="card c4r-modal" role="dialog" aria-modal="true" aria-labelledby={`${id}-title`}>
      <h3 id={`${id}-title`}>Add proof for {skill.skill_name}</h3>
      <p className="muted">Optional. A GitHub repository that is yours and uses this skill, or a certificate from a trusted site, gives a provisional level of 3/5. An uploaded certificate file counts as 2/5 until a reviewer checks it. Component 01 can confirm a higher level later.</p>
      {type === 'github' && <p className="muted">We compare the repository owner and contributors with the GitHub username in your Component 01 CV upload, then look for signs of {skill.skill_name} in its languages, topics, README and files.</p>}
      <form className="c4r-evidence-form" onSubmit={handleSubmit} noValidate>
        <fieldset>
          <legend>Type of proof</legend>
          {PROOF_TYPES.map((option, i) => <label key={option.value} className="c4r-radio">
            <input type="radio" name={`${id}-type`} value={option.value} checked={type === option.value} autoFocus={i === 0}
              onChange={() => { setType(option.value); setError('') }} />
            <span><strong>{option.label}</strong><small>{option.hint}</small></span>
          </label>)}
        </fieldset>
        {isFile
          ? <><label htmlFor={`${id}-file`}>Certificate file</label>
            <input id={`${id}-file`} type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
              onChange={event => { setFile(event.target.files?.[0] || null); setError('') }} /></>
          : <><label htmlFor={`${id}-url`}>Link</label>
            <input id={`${id}-url`} type="url" value={url} placeholder="https://" aria-invalid={Boolean(error)}
              aria-describedby={error ? `${id}-error` : undefined} onChange={event => { setUrl(event.target.value); setError('') }} /></>}
        <label htmlFor={`${id}-description`}>Description <small className="muted">(optional)</small></label>
        <textarea id={`${id}-description`} rows={2} maxLength={500} value={description} onChange={event => setDescription(event.target.value)}
          placeholder="What does this show about your skill?" />
        {error && <p className="c4-field-error" id={`${id}-error`} role="alert">{error}</p>}
        <div className="c4r-actions c4r-modal-actions">
          <button type="button" className="button-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" disabled={saving}>{saving ? 'Checking…' : 'Submit'}</button>
        </div>
      </form>
    </div>
  </div>
}

function EvidenceBadge({ skill, onRetry }) {
  const status = skill.evidence_status
  if (status === 'pending') return <div className="c4r-evidence-status is-pending">
    <span>Proof submitted – pending{skill.evidence_level ? ` (counts as ${Math.round(skill.evidence_level)}/5 for now)` : ''}</span>
    {skill.evidence_detail && <small className="c4r-evidence-reason">{skill.evidence_detail} See “My evidence” below.</small>}
  </div>
  if (status === 'provisional') return <p className="c4r-evidence-status is-provisional">Provisionally verified ({Math.round(skill.evidence_level ?? 3)}/5)</p>
  if (status === 'verified') return <p className="c4r-evidence-status is-verified">✓ Verified</p>
  if (status === 'rejected') return <div className="c4r-evidence-status is-rejected">
    <span>Proof not accepted: {skill.evidence_detail || 'it could not be matched to this skill.'}</span>
    <button type="button" className="button-secondary" onClick={onRetry}>Try again</button>
  </div>
  return null
}

function SkillGaps({ gaps, onEvidenceChange }) {
  const { summary, skills } = gaps
  const [proofSkill, setProofSkill] = useState(null)
  const canAddProof = hasCvSession()
  return <section className="card c4r-section" aria-labelledby="c4r-gaps">
    <div className="c4r-section-title"><span className="step-number">02</span><h2 id="c4r-gaps">Skill gap analysis</h2></div>
    <p className="muted">Your CV evidence (Component 01) compared with the O*NET requirements for this career. Self-ratings are shown alongside but never count as proficiency.</p>
    <div className="c4r-stats">
      <div><strong>{summary.gaps + (summary.unverified || 0)}</strong><span>Gaps ({summary.critical} critical)</span></div>
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
            {skill.status === 'unverified' && skill.message && <p className="c4r-claim-message">{skill.message}</p>}
            <EvidenceBadge skill={skill} onRetry={() => setProofSkill(skill)} />
            {skill.status === 'unverified' && <div className="c4r-actions c4r-evidence-actions">
              {skill.evidence_status !== 'rejected' && <button type="button" className="button-secondary" disabled={!canAddProof}
                title={canAddProof ? undefined : 'Upload your CV in Component 01 first'} onClick={() => setProofSkill(skill)}>+ Add proof</button>}
              <Link className="button button-secondary" to="/component01">Upload updated CV</Link>
            </div>}
          </div>
        </div>
        <dl className="c4r-skill-facts">
          <div><dt>CV evidence</dt><dd><LevelBar current={skill.current_level} required={skill.required_level} /><small>{skill.current_level}/5 · needed {skill.required_level}/5</small></dd></div>
          <div><dt>Your confidence</dt><dd>{skill.not_studied ? 'Not studied' : skill.self_rating == null ? 'Not rated' : `${skill.self_rating}/5`}</dd></div>
          <div><dt>Evidence source</dt><dd>{skill.evidence_source === 'none' ? 'Not found in CV'
            : skill.evidence_source === 'CV' || skill.evidence_source.startsWith('derived') ? `${skill.evidence_source}${skill.evidence_strength ? ` (${skill.evidence_strength})` : ''}`
            : skill.evidence_source}</dd></div>
        </dl>
        {skill.notes.filter(n => !n.startsWith('No self-rating')).map(note => <p key={note} className="c4r-note">{note}</p>)}
      </article>)}
    </div>
    {proofSkill && <ProofModal skill={proofSkill} onClose={() => setProofSkill(null)}
      onSubmitted={response => { setProofSkill(null); onEvidenceChange(response) }} />}
  </section>
}

const CHECK_RESULT = {
  passed: { icon: '✓', label: 'Passed', className: 'is-passed' },
  failed: { icon: '✗', label: 'Failed', className: 'is-failed' },
  not_checked: { icon: '–', label: 'Not checked', className: 'is-skipped' },
}
const PROOF_LABEL = { github: 'GitHub repository', certificate_link: 'Certificate link', certificate_file: 'Certificate file' }

function evidenceStatusLabel(item) {
  if (item.status === 'pending') return item.proof_type === 'certificate_file'
    ? `Pending review (counts as ${Math.round(item.provisional_level ?? 2)}/5)` : 'Pending'
  if (item.status === 'provisional') return `Provisionally verified (${Math.round(item.provisional_level ?? 3)}/5)`
  if (item.status === 'verified') return `✓ Verified${item.verified_level != null ? ` (${Math.round(item.verified_level)}/5)` : ''}`
  if (item.status === 'rejected') return 'Not accepted'
  return item.status
}

function EvidencePanel({ version, onEvidenceChange }) {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(null)                     // { id, action: 'remove' | 'recheck' }

  useEffect(() => {
    let active = true
    listEvidence().then(list => { if (active) { setItems(list); setError('') } }).catch(err => { if (active) setError(err.message) })
    return () => { active = false }
  }, [version])

  async function run(item, action) {
    setBusy({ id: item.evidence_id, action })
    setError('')
    try { onEvidenceChange(await (action === 'remove' ? deleteEvidence : recheckEvidence)(item.evidence_id)) }
    catch (err) { setError(err.message) }
    finally { setBusy(null) }
  }

  if (!hasCvSession() || (!items.length && !error)) return null
  const isBusy = (item, action) => busy?.id === item.evidence_id && busy.action === action
  return <section className="card c4r-section" aria-labelledby="c4r-evidence-title">
    <h2 id="c4r-evidence-title">My evidence</h2>
    <p className="muted">Proof you added for claimed skills, with what was checked. Removing or re-checking an item updates your roadmap.</p>
    {error && <p className="error-message" role="alert">{error}</p>}
    <ul className="c4r-evidence-list">
      {items.map(item => <li key={item.evidence_id} className={`c4r-evidence-item is-${item.status}`}>
        <div className="c4r-evidence-head">
          <div>
            <strong>{item.skill_name}</strong>
            <small className="muted"> · {PROOF_LABEL[item.proof_type] || item.proof_type}</small>
            <p className="c4r-proof-cell">{item.url
              ? <a href={item.url} target="_blank" rel="noopener noreferrer">{item.url.replace(/^https:\/\//, '')}</a>
              : item.file_name}</p>
          </div>
          <span className={`c4r-evidence-status is-${item.status}`}>{evidenceStatusLabel(item)}</span>
        </div>
        {item.status_reason && <p className="c4r-evidence-reason">{item.status_reason}</p>}
        {item.check_details?.length > 0 && <details className="c4r-checks" open={item.status !== 'provisional' && item.status !== 'verified'}>
          <summary>What we checked</summary>
          <ul>{item.check_details.map((step, i) => {
            const result = CHECK_RESULT[step.result] || CHECK_RESULT.not_checked
            return <li key={`${step.check}-${i}`} className={result.className}>
              <span className="c4r-check-icon" aria-hidden="true">{result.icon}</span>
              <span><strong>{step.check}</strong> <span className="sr-only">{result.label}</span>{step.detail && <small>{step.detail}</small>}</span>
            </li>
          })}</ul>
        </details>}
        <div className="c4r-actions c4r-evidence-actions">
          {item.can_recheck && <button type="button" className="button-secondary" disabled={Boolean(busy)} onClick={() => run(item, 'recheck')}>
            {isBusy(item, 'recheck') ? 'Checking…' : 'Check again'}</button>}
          <button type="button" className="button-secondary c4r-remove" disabled={Boolean(busy)} onClick={() => run(item, 'remove')}>
            {isBusy(item, 'remove') ? 'Removing…' : 'Remove'}</button>
        </div>
      </li>)}
    </ul>
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
            {p.factors.map((f, i) => <span key={f.key} className={FACTOR_CLASS[i]} style={{ width: `${f.points * (p.adjustment_factor ?? 1) * 100}%` }} />)}
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
    <p className="c4r-caution"><Icon name="spark" size={15} />Your roadmap is based on your CV. Adding proof for claimed skills is optional and will update your roadmap automatically.</p>
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
  const [evidenceVersion, setEvidenceVersion] = useState(0)

  // Proof added or removed: use the regenerated roadmap from the response (or reload it).
  function handleEvidenceChange(response) {
    if (response?.analysis?.assessment?.assessment_id === assessmentId) setState(s => ({ ...s, result: response.analysis }))
    else setReload(v => v + 1)
    setEvidenceVersion(v => v + 1)
  }

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
    <SkillGaps gaps={result.skill_gaps} onEvidenceChange={handleEvidenceChange} />
    <EvidencePanel version={evidenceVersion} onEvidenceChange={handleEvidenceChange} />
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
