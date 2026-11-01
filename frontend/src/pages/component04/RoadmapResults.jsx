// Owner: Dewmi - Component 04: explainable results for a Career Readiness Assessment, arranged in tabs.
// Dashboard, skill gaps, confidence, learning style, priorities, the adaptive roadmap (roadmap steps with the
// learning coach's lessons inside), resources and roadmap updates. All values come from the C4 analysis and plan APIs.
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../../components/Icon.jsx'
import { ErrorState, PageLoader, ReloadButton, SkeletonRoadmap, SkeletonSkillGap } from '../../components/loading/index.js'
import { cached, hasCached, peek, prime } from '../../api/resourceCache.js'
import { Activity, CoachRules, NextActivityCard, RoadmapEvents, SKILL_STATUS, SkillLessons, activityRequest, lessonTotals,
  lessonsBySkill, useLearningPlan } from './LearningCoach.jsx'
import { deleteEvidence, generateLessons, getAnalysis, hasCvSession, listEvidence, recheckEvidence, submitEvidence } from './assessmentApi.js'
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
    <div className="c4r-section-title"><h2 id="c4r-readiness">Career readiness score</h2></div>
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
    <div className="c4r-section-title"><h2 id="c4r-gaps">Skill gap analysis</h2></div>
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
    <div className="c4r-section-title"><h2 id="c4r-priorities">Skill priorities</h2></div>
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

function RoadmapStep({ step, lessons, ai, onOpen, onGenerate, generating }) {
  const active = ['active', 'revision'].includes(lessons?.status)
  return <details className={`c4r-step ${active ? 'is-current' : ''}`} open={active}>
    <summary>
      <span className="c4r-step-number">{step.step}</span>
      <span className="c4r-step-title"><strong>{step.skill_name}</strong><small>{step.reason}</small>
        {step.entry_stage && <span className="c4r-placement-tags">
          <span className="c4r-tag">Start: {step.entry_stage} → Target: {step.target_stage}</span>
          {step.skipped_stages?.length > 0 && <span className="c4r-tag is-skipped">Skipped: {step.skipped_stages.join(', ')}</span>}
          {lessons && <span className={`c4r-tag c4l-chip status-${lessons.status}`}>{SKILL_STATUS[lessons.status] || lessons.status}</span>}
        </span>}
        {lessons?.progress && <span className="c4l-progress" aria-label={`${lessons.progress.done} of ${lessons.progress.total} lessons done`}>
          <span style={{ width: `${lessons.progress.percent}%` }} />
        </span>}
      </span>
      <span className="c4r-step-meta"><span className={`c4r-status ${STATUS[step.status].className}`}>{STATUS[step.status].label}</span><small>Weeks {step.start_week}–{step.end_week} · {step.estimated_hours} h</small></span>
    </summary>
    <div className="c4r-step-body">
      {step.placement_reason && <p className="c4r-placement">{step.placement_reason}</p>}
      <SkillLessons skill={lessons} ai={ai} onOpen={onOpen} onGenerate={onGenerate} busy={generating === step.skill_id} />
      {step.prerequisites.length > 0 && <p className="muted">Builds on: {step.prerequisites.join(', ')}</p>}
      <div className="c4r-step-grid">
        <div><h4>Learning activities</h4><ul>{step.activities.map(a => <li key={a}>{a}</li>)}</ul></div>
        <div><h4>Practical project</h4><p>{step.project}</p></div>
        <div><h4>Milestones</h4><ul className="c4r-milestones">{step.milestones.map(m => <li key={m}><Icon name="check" size={14} />{m}</li>)}</ul></div>
        <div><h4>Recommended resources</h4>{step.resources.length ? <ul className="c4r-resources">{step.resources.map(r => <Resource key={r.resource_id} resource={r} />)}</ul> : <p className="muted">{step.resource_note || 'No resources are available for this skill in the current dataset.'}</p>}</div>
      </div>
    </div>
  </details>
}

function LearnerProfile({ profile }) {
  if (!profile) return null
  return <div className={`c4r-profile profile-${profile.level.toLowerCase()}`}>
    <div className="c4r-profile-head">
      <h3>Your learning profile</h3>
      <span className="c4r-profile-level">{profile.level}</span>
      <small className="muted">{profile.score}/{profile.max_score} points</small>
    </div>
    <ul>{profile.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul>
    <p className="c4r-profile-pace"><Icon name="spark" size={15} />{profile.pace_note}</p>
    <details className="c4r-breakdown">
      <summary>How your profile is used</summary>
      <p className="muted">{profile.rule}</p>
      <p className="muted">Resource types after your own learning methods: {profile.resource_type_order.join(' → ')}. It also sets project difficulty and the pace note. Each skill still starts at the level your own evidence shows.</p>
    </details>
  </div>
}

// Adaptive roadmap: the roadmap steps (order, placement, weeks, priority reasons) with each skill's lessons inside.
// An opened lesson or quiz replaces the list; closing it returns to the roadmap.
function AdaptiveRoadmap({ result, coach, request, onOpen, onClose, onAttempt, onGenerate, generating }) {
  const { roadmap } = result
  const lessons = lessonsBySkill(coach.plan)
  if (request) return <section className="card c4r-section">
    <Activity assessmentId={result.assessment.assessment_id} request={request} onDone={onAttempt} onClose={onClose} />
  </section>
  return <section className="card c4r-section" aria-labelledby="c4r-roadmap">
    <div className="c4r-section-title"><h2 id="c4r-roadmap">Adaptive learning roadmap</h2></div>
    <p className="muted">Each skill starts at the level your own evidence shows, prerequisites come first, and each step has its lessons
      inside. Lessons open in order; passing their quizzes updates this roadmap and your readiness score.</p>
    {coach.plan ? <NextActivityCard plan={coach.plan} onOpen={onOpen} />
      : coach.signedIn ? <p className="c4r-notice" role="status">{coach.loading ? 'Loading your lessons…' : coach.error || 'Lessons are not available right now.'}</p>
        : <p className="c4r-notice">Upload your CV in Component 01 to unlock the interactive lessons. Your progress is saved to your own profile.</p>}
    {coach.error && coach.plan && <p className="error-message" role="alert">{coach.error}</p>}
    {roadmap.total_steps === 0 ? <p>Your CV evidence already meets every requirement for this career. Keep your skills current and add new evidence to your CV.</p> : <>
      <div className="c4r-stats">
        <div><strong>{roadmap.total_steps}</strong><span>Skills to develop</span></div>
        <div><strong>{Math.round(roadmap.total_hours)}</strong><span>Estimated hours</span></div>
        <div><strong>{roadmap.total_weeks}</strong><span>Weeks at {roadmap.weekly_hours} h/week</span></div>
      </div>
      <div className="c4r-stages">
        {roadmap.stages.map(stage => <div key={stage.stage} className={`c4r-stage stage-${stage.stage.toLowerCase()}`}>
          <div className="c4r-stage-head">
            <h3>{stage.stage}</h3>
            <small>Weeks {stage.start_week}–{stage.end_week} · {Math.round(stage.estimated_hours)} h</small>
          </div>
          <p className="c4r-stage-milestone"><Icon name="check" size={15} />{stage.milestone}</p>
          {stage.steps.map(step => <RoadmapStep key={step.step} step={step} lessons={lessons[step.skill_id]} ai={coach.plan?.ai || {}}
            onOpen={onOpen} onGenerate={onGenerate} generating={generating} />)}
        </div>)}
      </div>
    </>}
    {coach.plan && <CoachRules plan={coach.plan} />}
  </section>
}

// ------------------------------------------------------------------ dashboard, confidence, learning style, resources, updates
function Dashboard({ result, coach, onOpen, onTab }) {
  const { skill_gaps: { summary }, roadmap } = result
  const totals = lessonTotals(coach.plan)
  return <>
    {coach.plan ? <NextActivityCard plan={coach.plan} onOpen={onOpen} />
      : !coach.loading && <p className="c4r-notice" role="status">{coach.error ||
        'Upload your CV in Component 01 and submit your assessment to unlock the interactive lessons.'}</p>}
    <div className="c4r-kpis">
      <button type="button" className="c4r-kpi" onClick={() => onTab('gaps')}><strong>{summary.met}/{summary.required}</strong><span>Required skills met</span></button>
      <button type="button" className="c4r-kpi" onClick={() => onTab('roadmap')}><strong>{roadmap.total_steps}</strong><span>Skills to develop</span></button>
      <button type="button" className="c4r-kpi" onClick={() => onTab('roadmap')}>
        <strong>{coach.plan ? `${totals.percent}%` : '—'}</strong>
        <span>{coach.plan ? `Lessons done (${totals.done} of ${totals.total} topics)` : 'Lessons done'}</span></button>
      <button type="button" className="c4r-kpi" onClick={() => onTab('roadmap')}><strong>{roadmap.total_weeks} wks</strong><span>Estimated at {roadmap.weekly_hours} h/week</span></button>
    </div>
    <Readiness readiness={result.readiness} assessment={result.assessment} />
  </>
}

const CONFIDENCE_GROUPS = [
  { key: 'claimed', label: 'Claimed – not verified', className: 'is-claimed', text: 'You rated yourself 4–5/5 but your CV shows little or no evidence. A quick check in the lessons, a project or proof can confirm it.' },
  { key: 'over', label: 'Rated higher than your CV evidence', className: 'is-over', text: 'Your confidence is higher than the evidence in your CV. Confidence never counts as proficiency, so show the skill in practical work.' },
  { key: 'under', label: 'CV evidence stronger than your rating', className: 'is-under', text: 'Your CV shows more than you think. You may be underestimating yourself.' },
  { key: 'aligned', label: 'No large mismatch', className: 'is-aligned', text: 'Your rating and your CV evidence are close enough that the analysis does not flag them.' },
]
const confidenceGroup = s => s.status === 'unverified' ? 'claimed' : s.overconfident ? 'over' : s.underconfident ? 'under' : 'aligned'

// Self-rating (1–5, from the assessment form) against CV evidence (0–5, Component 01) for every rated skill.
function ConfidenceChart({ skills }) {
  const W = 420, H = 300, L = 48, B = 40, T = 16, R = 16
  const x = v => L + (v / 5) * (W - L - R)
  const y = v => H - B - (v / 5) * (H - B - T)
  const points = {}
  skills.forEach(s => { const k = `${s.current_level}:${s.self_rating}`; (points[k] ||= { lv: s.current_level, r: s.self_rating, items: [] }).items.push(s) })
  return <svg className="c4r-confidence-chart" viewBox={`0 0 ${W} ${H}`} role="img"
    aria-label={`Self-rating against CV evidence for ${skills.length} skills`}>
    {[0, 1, 2, 3, 4, 5].map(v => <g key={v}>
      <line x1={x(v)} x2={x(v)} y1={y(0)} y2={y(5)} className="grid" /><line x1={x(0)} x2={x(5)} y1={y(v)} y2={y(v)} className="grid" />
      <text x={x(v)} y={H - B + 16} textAnchor="middle">{v}</text><text x={L - 10} y={y(v) + 4} textAnchor="end">{v}</text>
    </g>)}
    <line x1={x(0)} y1={y(0)} x2={x(5)} y2={y(5)} className="diagonal" />
    <text x={(L + W - R) / 2} y={H - 4} textAnchor="middle" className="axis">CV evidence level (Component 01)</text>
    <text transform={`translate(12 ${(T + H - B) / 2}) rotate(-90)`} textAnchor="middle" className="axis">Your self-rating</text>
    {Object.values(points).map(p => {
      const group = CONFIDENCE_GROUPS.find(g => g.key === confidenceGroup(p.items[0]))
      const label = p.items.length > 1 ? `${p.items[0].skill_name} +${p.items.length - 1}` : p.items[0].skill_name
      return <g key={`${p.lv}:${p.r}`} className={`point ${group.className}`}>
        <title>{p.items.map(s => s.skill_name).join(', ')}: self-rating {p.r}/5, CV level {p.lv}/5</title>
        <circle cx={x(p.lv)} cy={y(p.r)} r={5 + Math.min(p.items.length, 5)} />
        <text x={p.lv >= 3 ? x(p.lv) - 10 : x(p.lv) + 10} y={y(p.r) - 8} textAnchor={p.lv >= 3 ? 'end' : 'start'}>
          {label.length > 30 ? `${label.slice(0, 29)}…` : label}</text>
      </g>
    })}
  </svg>
}

function ConfidenceAnalysis({ gaps, onTab }) {
  const rated = gaps.skills.filter(s => s.self_rating != null)
  const groups = CONFIDENCE_GROUPS.map(g => ({ ...g, skills: rated.filter(s => confidenceGroup(s) === g.key) }))
  return <section className="card c4r-section" aria-labelledby="c4r-confidence">
    <div className="c4r-section-title"><h2 id="c4r-confidence">Confidence analysis</h2></div>
    <p className="muted">Your self-ratings from the assessment compared with the evidence Component 01 found in your CV. Points on the
      diagonal match; points above it are rated higher than the evidence. Confidence never counts as proficiency: it flags claims to check
      and adds the "low self-confidence" factor to skill priorities.</p>
    {rated.length === 0 ? <p className="c4r-notice">No self-ratings were collected for this career's skills.</p> : <div className="c4r-confidence">
      <ConfidenceChart skills={rated} />
      <div className="c4r-confidence-groups">
        {groups.filter(g => g.skills.length).map(g => <div key={g.key} className={`c4r-confidence-group ${g.className}`}>
          <h3><span className="c4r-dot" />{g.label} <small>({g.skills.length})</small></h3>
          {g.text && <p className="muted">{g.text}</p>}
          <ul>{g.skills.map(s => <li key={s.skill_id}><strong>{s.skill_name}</strong>
            <span>rated {s.self_rating}/5 · CV {s.current_level}/5{s.current_level < s.required_level ? ` · needed ${s.required_level}/5` : ''}</span></li>)}</ul>
        </div>)}
      </div>
    </div>}
    <div className="c4r-actions"><button type="button" className="button-secondary" onClick={() => onTab('gaps')}>See the skill gaps</button></div>
  </section>
}

const METHOD_LABELS = {
  online_courses: 'Online courses', video_tutorials: 'Video tutorials', reading: 'Reading documentation and books',
  hands_on_projects: 'Hands-on projects', interactive_exercises: 'Interactive coding exercises', instructor_led: 'Instructor-led classes',
  group_learning: 'Group learning', other: 'Other',
}
const LESSON_VERSION = {
  Novice: 'Lessons open in the step-by-step version, with extra support and simpler steps.',
  Developing: 'Lessons open in the standard version at your level.',
  Experienced: 'Lessons open in the challenge version, with less beginner support and a harder task.',
}

function LearningStyle({ result, onEdit }) {
  const methods = result.inputs.learning_methods || []
  const profile = result.roadmap.learner_profile || result.learner_profile
  return <section className="card c4r-section" aria-labelledby="c4r-style">
    <div className="c4r-section-title"><h2 id="c4r-style">Learning style</h2></div>
    <p className="muted">How you said you like to learn (assessment form) and how C4 adapts your roadmap and lessons to it.</p>
    <div className="c4r-methods">
      {Object.entries(METHOD_LABELS).map(([key, label]) => <span key={key} className={`c4r-method-chip ${methods.includes(key) ? 'is-selected' : ''}`}>
        {methods.includes(key) && <Icon name="check" size={14} />}{label}</span>)}
    </div>
    <p className="muted">Weekly study time: {result.inputs.weekly_study_hours} hours.
      <button type="button" className="c4l-link" onClick={onEdit}>Change in my assessment</button></p>
    <div className="c4r-adapts">
      <h3>How your roadmap adapts</h3>
      <ul>
        <li><strong>Resources:</strong> ranked by your learning methods first{methods.length ? ` (${methods.map(m => METHOD_LABELS[m] || m).join(', ')})` : ''}, then by your learner profile.</li>
        {profile && <li><strong>Lessons:</strong> {LESSON_VERSION[profile.level] || ''} After a quiz the version changes with your result (focused practice or step by step).</li>}
        {methods.includes('hands_on_projects') && <li><strong>Practical first:</strong> lessons show the practical task before the practice questions.</li>}
        <li><strong>Pace:</strong> week estimates use your {result.inputs.weekly_study_hours} hours per week.</li>
      </ul>
    </div>
    <LearnerProfile profile={profile} />
  </section>
}

function Resources({ roadmap }) {
  const [type, setType] = useState('all')
  const steps = roadmap.stages.flatMap(stage => stage.steps)
  const types = [...new Set(steps.flatMap(s => s.resources.map(r => r.type)))]
  return <section className="card c4r-section" aria-labelledby="c4r-res">
    <div className="c4r-section-title"><h2 id="c4r-res">Recommended resources</h2></div>
    <p className="muted">Level-matched resources for every roadmap skill, ranked by your learning methods and profile. Resources below
      your starting stage are never shown.</p>
    {types.length > 1 && <div className="c4r-filter" role="group" aria-label="Filter by type">
      {['all', ...types].map(t => <button key={t} type="button" className={`c4r-method-chip ${type === t ? 'is-selected' : ''}`}
        aria-pressed={type === t} onClick={() => setType(t)}>{t === 'all' ? 'All' : t}</button>)}
    </div>}
    {steps.map(step => {
      const list = step.resources.filter(r => type === 'all' || r.type === type)
      if (!list.length) return null
      return <div key={step.skill_id} className="c4r-res-group">
        <h3>{step.step}. {step.skill_name} <small className="muted">{step.entry_stage} → {step.target_stage}</small></h3>
        <div className="c4r-res-grid">{list.map(r => <article key={r.resource_id} className="c4r-res-card">
          <div className="c4r-tags"><span className="c4r-tag">{r.type}</span><span className="c4r-tag">{r.level}</span>{r.is_free && <span className="c4r-tag">Free</span>}</div>
          <h4>{r.title}</h4>
          <small className="muted">{[r.provider, r.duration_hours ? `${r.duration_hours} h` : null, r.rating ? `rating ${r.rating}` : null].filter(Boolean).join(' · ')}</small>
          <p><strong>Why recommended:</strong> {r.why}</p>
          {r.url && <a className="button button-secondary" href={r.url} target="_blank" rel="noopener noreferrer">Open resource <Icon name="arrow" size={13} /></a>}
        </article>)}</div>
      </div>
    })}
  </section>
}

function Updates({ result, coach }) {
  const { assessment } = result
  return <section className="card c4r-section" aria-labelledby="c4r-updates">
    <div className="c4r-section-title"><h2 id="c4r-updates">Roadmap updates</h2></div>
    <p className="muted">Your roadmap is rebuilt automatically when you pass lessons and quick checks, add or remove proof, update your
      assessment or upload an updated CV in Component 01. Changes come from these rules, not from guesses.</p>
    {assessment.changes.map(message => <p key={message} className="c4r-notice" role="status">{message}</p>)}
    <h3>Why your roadmap changed</h3>
    {coach.plan ? <RoadmapEvents events={coach.plan.events} />
      : <p className="muted">{coach.signedIn ? 'Loading…' : 'Upload your CV in Component 01 to save your learning progress.'}</p>}
    {assessment.history.length > 1 && <>
      <h3>Assessment history</h3>
      <div className="table-scroll"><table className="c4r-history">
        <thead><tr><th>Submitted</th><th>Career</th><th>Readiness at submission</th></tr></thead>
        <tbody>{assessment.history.map(h => <tr key={h.assessment_id} className={h.assessment_id === assessment.assessment_id ? 'is-current' : ''}>
          <td>{formatDate(h.submitted_at)}</td><td>{h.career_name}</td><td>{h.readiness_score == null ? '—' : Math.round(h.readiness_score)}</td>
        </tr>)}</tbody>
      </table></div>
    </>}
  </section>
}

const TABS = [
  { key: 'dashboard', label: 'Roadmap Dashboard' },
  { key: 'gaps', label: 'Skill Gap Overview' },
  { key: 'confidence', label: 'Confidence Analysis' },
  { key: 'style', label: 'Learning Style' },
  { key: 'priority', label: 'Priority Engine' },
  { key: 'roadmap', label: 'Adaptive Roadmap' },
  { key: 'resources', label: 'Resources' },
  { key: 'updates', label: 'Roadmap Updates' },
]
const TAB_KEY = 'careernova-c4-tab'
const savedTab = () => { try { return TABS.some(t => t.key === sessionStorage.getItem(TAB_KEY)) ? sessionStorage.getItem(TAB_KEY) : 'dashboard' } catch { return 'dashboard' } }

function Method({ result }) {
  const { method, model_info: model } = result
  return <details className="card c4r-method">
    <summary>Method, data sources and limitations</summary>
    <h3>Skill gap analysis</h3><p>{method.gap_analysis}</p>
    <h3>Resources and roadmap</h3><p>{method.resource_ranking}</p><p>{method.roadmap_ordering}</p>
    {method.adaptive_placement && <><h3>Adaptive placement</h3><p>{method.adaptive_placement}</p></>}
    {method.learner_profile && <><h3>Learner profile</h3><p>{method.learner_profile}</p></>}
    {method.learning_coach && <><h3>Learning coach</h3><p>{method.learning_coach}</p></>}
    <h3>Data sources</h3><ul>{method.data_sources.map(s => <li key={s}>{s}</li>)}</ul>
    <h3>Limitations</h3><ul>{method.limitations.map(s => <li key={s}>{s}</li>)}</ul>
    <p className="muted">Models: {model.gap_model} (skill gap), {model.readiness_model} (readiness) · C4 {model.versions?.c4} · trained {model.versions?.trained_at} on {model.versions?.training_data} · O*NET {model.versions?.onet}</p>
  </details>
}

export default function RoadmapResults({ assessmentId, onEdit, onNew }) {
  // The last analysis is shown at once on a revisit and refreshed in the background.
  const cacheKey = `c04:analysis:${assessmentId}`
  const [state, setState] = useState(() => ({ loading: true, error: '', result: peek(cacheKey) ?? null }))
  const [fresh] = useState(() => !hasCached(cacheKey))
  const [reload, setReload] = useState(0)
  const [evidenceVersion, setEvidenceVersion] = useState(0)
  const [tab, setTabState] = useState(savedTab)
  const [request, setRequest] = useState(null)             // the lesson / quick check open in the Adaptive Roadmap tab
  const [generating, setGenerating] = useState(null)
  const coach = useLearningPlan(assessmentId, evidenceVersion)
  const tabsRef = useRef(null)

  // Proof added or removed: use the regenerated roadmap from the response (or reload it).
  function handleEvidenceChange(response) {
    if (response?.analysis?.assessment?.assessment_id === assessmentId) { prime(cacheKey, response.analysis); setState(s => ({ ...s, result: response.analysis })) }
    else setReload(v => v + 1)
    setEvidenceVersion(v => v + 1)                           // the lesson plan follows the new roadmap
  }

  // A quiz or quick check was graded: show the regenerated roadmap and the new lesson plan.
  function handleAttempt(response) {
    if (response.plan) coach.setPlan(response.plan)
    if (response.analysis?.assessment?.assessment_id === assessmentId) { prime(cacheKey, response.analysis); setState(s => ({ ...s, result: response.analysis })) }
  }

  async function handleGenerate(skillId) {
    setGenerating(skillId)
    try { coach.setPlan(await generateLessons(assessmentId, skillId)) }
    catch (error) { coach.setError(error.message) }
    finally { setGenerating(null) }
  }

  const scrollToTabs = () => tabsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  function setTab(key) {
    setTabState(key)
    try { sessionStorage.setItem(TAB_KEY, key) } catch { /* storage unavailable */ }
  }
  function openActivity(next) {
    setRequest(activityRequest(next))
    setTab('roadmap')
    scrollToTabs()
  }
  function closeActivity() {
    setRequest(null)
    scrollToTabs()
  }

  useEffect(() => {
    let active = true
    // Keep the current roadmap on screen while the same assessment refreshes.
    setState(prev => ({ loading: true, error: '', result: prev.result?.assessment?.assessment_id === assessmentId ? prev.result : peek(cacheKey) ?? null }))
    cached(cacheKey, () => getAnalysis(assessmentId))
      .then(result => { if (active) setState({ loading: false, error: '', result }) })
      .catch(error => { if (active) setState(prev => ({ loading: false, error: error.message, result: prev.result })) })
    return () => { active = false }
  }, [assessmentId, reload]) // eslint-disable-line react-hooks/exhaustive-deps -- cacheKey follows assessmentId

  const refresh = () => setReload(v => v + 1)
  if (state.loading && !state.result) return <PageLoader variant="roadmap" delay={0} label="Analysing your skills and building your roadmap…"
    skeleton={<div className="sk-stack"><SkeletonSkillGap /><SkeletonRoadmap /></div>} />
  if (state.error && !state.result) return <ErrorState title="We could not build your roadmap" message={state.error} onRetry={refresh}>
    <button type="button" className="button-secondary" onClick={onEdit}>Edit my assessment</button>
  </ErrorState>

  const { result } = state
  const index = TABS.findIndex(t => t.key === tab)
  const next = TABS[index + 1]
  return <div className={`c4r ${fresh ? 'fx-stagger' : ''}`} aria-busy={state.loading}>
    {state.error && <ErrorState title="We could not refresh your roadmap" message={state.error} onRetry={refresh} />}
    <section className="card c4r-overview">
      <div>
        <p className="eyebrow">TARGET CAREER</p>
        <h2>{result.target_career.career_name}</h2>
        <p className="muted">Assessment submitted {formatDate(result.assessment.submitted_at)} · CV assessed {formatDate(result.assessment.cv_assessed_at)}</p>
      </div>
      <div className="c4r-actions">
        <button type="button" onClick={onEdit}>Update my assessment</button>
        <button type="button" className="button-secondary" onClick={onNew}>Choose another career</button>
        <ReloadButton onClick={refresh} loading={state.loading} label="Refresh roadmap" />
      </div>
      {!result.candidate_id && hasCvSession() ? <div className="c4r-notice c4r-link-cv" role="status">
        <span>Your CV is uploaded, but this assessment was submitted before it, so it does not use your CV evidence and the lessons
          are locked. Submit the assessment again to link it to your CV.</span>
        <button type="button" onClick={onEdit}>Submit again with my CV</button>
      </div> : !result.candidate_id && <div className="c4r-notice c4r-link-cv" role="status">
        <span>Upload your CV in Component 01, then submit this assessment again: your roadmap will use your CV evidence and the
          interactive lessons will unlock.</span>
        <Link className="button" to="/component01">Upload my CV</Link>
      </div>}
      {[...result.assessment.changes, ...result.warnings.filter(w => result.candidate_id || !w.startsWith('No CV skills'))]
        .map(message => <p key={message} className="c4r-notice" role="status">{message}</p>)}
      {result.inputs.cv_skills_not_in_catalogue.length > 0 && <p className="c4r-notice">CV skills not covered by the C4 skills catalogue (not used): {result.inputs.cv_skills_not_in_catalogue.join(', ')}.</p>}
    </section>

    <div className="c4r-tabs" role="tablist" aria-label="Learning roadmap sections" ref={tabsRef}>
      {TABS.map(t => <button key={t.key} type="button" role="tab" id={`c4r-tab-${t.key}`} aria-selected={tab === t.key}
        aria-controls="c4r-tabpanel" className={tab === t.key ? 'is-active' : ''} onClick={() => setTab(t.key)}>
        {t.label}{t.key === 'roadmap' && request && <span className="c4r-tab-dot" title="A lesson is open" />}</button>)}
    </div>

    <div className="c4r-tabpanel" id="c4r-tabpanel" role="tabpanel" aria-labelledby={`c4r-tab-${tab}`}>
      {tab === 'dashboard' && <Dashboard result={result} coach={coach} onOpen={openActivity} onTab={setTab} />}
      {tab === 'gaps' && <>
        <SkillGaps gaps={result.skill_gaps} onEvidenceChange={handleEvidenceChange} />
        <EvidencePanel version={evidenceVersion} onEvidenceChange={handleEvidenceChange} />
      </>}
      {tab === 'confidence' && <ConfidenceAnalysis gaps={result.skill_gaps} onTab={setTab} />}
      {tab === 'style' && <LearningStyle result={result} onEdit={onEdit} />}
      {tab === 'priority' && (result.priorities.length ? <Priorities priorities={result.priorities} method={result.method} />
        : <section className="card c4r-section"><p>No skill gaps to prioritise: your evidence meets this career's requirements.</p></section>)}
      {tab === 'roadmap' && <AdaptiveRoadmap result={result} coach={coach} request={request} onOpen={openActivity}
        onClose={closeActivity} onAttempt={handleAttempt} onGenerate={handleGenerate} generating={generating} />}
      {tab === 'resources' && <Resources roadmap={result.roadmap} />}
      {tab === 'updates' && <Updates result={result} coach={coach} />}
    </div>

    {next && !(tab === 'roadmap' && request) && <div className="c4r-next-tab">
      <button type="button" onClick={() => { setTab(next.key); scrollToTabs() }}>View {next.label} <Icon name="arrow" size={14} /></button>
    </div>}
    <Method result={result} />
  </div>
}
