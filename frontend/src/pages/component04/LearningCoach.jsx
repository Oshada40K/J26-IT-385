// Owner: Dewmi - Component 04: adaptive learning tutor inside the roadmap page.
// Flow: next activity -> lesson adapted to the learner -> quiz (answers hidden until submitted) -> feedback and the
// tutor's decision (advance / targeted practice / re-teach / prerequisite) -> the regenerated roadmap and readiness.
import { useEffect, useState } from 'react'
import Icon from '../../components/Icon.jsx'
import { generateLessons, getLearningPlan, hasCvSession, openActivity, submitLearningAttempt } from './assessmentApi.js'
import './LearningCoach.css'

const TOPIC_STATE = {
  not_started: { label: 'Not started', className: '' },
  learning: { label: 'Learning', className: 'is-learning' },
  needs_revision: { label: 'Needs revision', className: 'is-revision' },
  mastered: { label: 'Mastered', className: 'is-mastered' },
  from_evidence: { label: 'Covered by your evidence', className: 'is-evidence' },
}
const SKILL_STATUS = {
  active: 'Learning now', revision: 'Revision', next: 'Next', upcoming: 'Upcoming', pending: 'Upcoming',
  completed: 'Lessons done', self_study: 'Self-study',
}
const DECISION = {
  advance: { title: 'Mastered – moving on', className: 'is-good' },
  targeted_practice: { title: 'Almost there – targeted practice', className: 'is-mid' },
  reteach: { title: 'Let’s learn this again, step by step', className: 'is-low' },
  prerequisite: { title: 'Going back to the basics first', className: 'is-low' },
  checkpoint_passed: { title: 'Checkpoint passed', className: 'is-good' },
  checkpoint_failed: { title: 'Some basics need work', className: 'is-mid' },
  claim_passed: { title: 'Your self-rating is supported', className: 'is-good' },
  claim_failed: { title: 'Your self-rating is not supported yet', className: 'is-mid' },
  test_out_passed: { title: 'Topic skipped', className: 'is-good' },
  test_out_failed: { title: 'Take the lesson first', className: 'is-mid' },
  practical_recorded: { title: 'Self-check recorded', className: 'is-mid' },
}
const formatDate = value => value ? new Date(value).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : ''

// ------------------------------------------------------------------ lesson content
function Visual({ visual }) {
  if (!visual?.columns) return null
  return <figure className="c4l-visual">
    <div className="table-scroll"><table>
      <thead><tr>{visual.columns.map(c => <th key={c}>{c}</th>)}</tr></thead>
      <tbody>{visual.rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>)}</tbody>
    </table></div>
    {visual.how_to_read && <figcaption>{visual.how_to_read}</figcaption>}
  </figure>
}

function Section({ section, rubric, onRubric }) {
  const list = items => <ul>{items.map(item => <li key={item}>{item}</li>)}</ul>
  return <section className={`c4l-part c4l-part-${section.kind}`}>
    <h4>{section.title}</h4>
    {section.text && <p>{section.text}</p>}
    {section.kind === 'steps' && <ol>{section.items.map(item => <li key={item}>{item}</li>)}</ol>}
    {['focus', 'key_ideas', 'mistakes'].includes(section.kind) && list(section.items)}
    {section.kind === 'visual' && <Visual visual={section.visual} />}
    {section.kind === 'worked_example' && <>
      <pre className="c4l-code"><code>{section.example.code}</code></pre>
      <ol>{section.example.steps.map(step => <li key={step}>{step}</li>)}</ol>
    </>}
    {section.kind === 'practical' && <>
      <fieldset className="c4l-rubric"><legend>Self-check</legend>
        {section.items.map((item, i) => <label key={item}>
          <input type="checkbox" checked={rubric.includes(i)} onChange={() => onRubric(i)} /> {item}
        </label>)}
      </fieldset>
      <p className="muted">{section.note}</p>
    </>}
  </section>
}

// ------------------------------------------------------------------ questions
// Prompts may start with a few lines of code; the last line is the question itself.
function Prompt({ text }) {
  const lines = String(text).split('\n')
  if (lines.length === 1) return text
  return <>{lines[lines.length - 1]}<pre className="c4l-code"><code>{lines.slice(0, -1).join('\n')}</code></pre></>
}

function Question({ q, index, value, onChange }) {
  const name = `c4l-${q.id}`
  return <fieldset className="c4l-question" aria-labelledby={`${name}-prompt`}>
    <div className="c4l-prompt" id={`${name}-prompt`}><span>{index + 1}.</span> <Prompt text={q.prompt} />{q.type === 'multi' && <small> (choose all that apply)</small>}</div>
    {q.type === 'single' && q.options.map((option, i) => <label key={option}>
      <input type="radio" name={name} checked={value === i} onChange={() => onChange(i)} /> {option}
    </label>)}
    {q.type === 'multi' && q.options.map((option, i) => {
      const chosen = value || []
      return <label key={option}>
        <input type="checkbox" checked={chosen.includes(i)}
          onChange={() => onChange(chosen.includes(i) ? chosen.filter(x => x !== i) : [...chosen, i])} /> {option}
      </label>
    })}
    {q.type === 'short' && <textarea rows={3} maxLength={2000} value={value || ''} aria-label={q.prompt}
      onChange={event => onChange(event.target.value)} placeholder="Write your answer in a sentence or two" />}
  </fieldset>
}

function QuestionForm({ questions, submitLabel, busy, onSubmit }) {
  const [answers, setAnswers] = useState({})
  const answered = questions.filter(q => answers[q.id] !== undefined && answers[q.id] !== '' &&
    !(Array.isArray(answers[q.id]) && answers[q.id].length === 0)).length
  return <form className="c4l-quiz" onSubmit={event => { event.preventDefault(); onSubmit(answers) }}>
    {questions.map((q, i) => <Question key={q.id} q={q} index={i} value={answers[q.id]}
      onChange={value => setAnswers(a => ({ ...a, [q.id]: value }))} />)}
    <div className="c4l-quiz-actions">
      <small className="muted">{answered} of {questions.length} answered{answered < questions.length ? ' – unanswered questions count as wrong' : ''}</small>
      <button type="submit" disabled={busy}>{busy ? 'Checking…' : submitLabel}</button>
    </div>
  </form>
}

function Feedback({ result, onContinue, onRetry }) {
  const { graded, decision, roadmap_update: update } = result
  const look = DECISION[decision.case] || { title: 'Result', className: 'is-mid' }
  return <div className="c4l-feedback" role="status">
    <div className={`c4l-decision ${look.className}`}>
      {graded.score != null && <strong className="c4l-score">{Math.round(graded.score * 100)}%</strong>}
      <div><h4>{look.title}</h4><p>{decision.message}</p>
        {decision.missed_concepts?.length > 0 && <p className="muted">Ideas to work on: {decision.missed_concepts.join(', ')}</p>}
      </div>
    </div>
    {update && <p className={`c4l-update ${update.changed ? 'is-changed' : ''}`}><Icon name="roadmap" size={15} /> {update.message}</p>}
    {graded.results?.length > 0 && <ol className="c4l-results">
      {graded.results.map(r => <li key={r.id} className={r.correct ? 'is-correct' : 'is-wrong'}>
        <div className="c4l-result-head"><Icon name={r.correct ? 'check' : 'close'} size={14} /> <div><Prompt text={r.prompt} /></div></div>
        {!r.correct && <p><strong>Your answer:</strong> {Array.isArray(r.your_answer) ? (r.your_answer.join(', ') || '—') : (r.your_answer || '—')}</p>}
        <p><strong>Correct answer:</strong> {Array.isArray(r.correct_answer) ? r.correct_answer.join(', ') : r.correct_answer}</p>
        {r.why_your_answer_is_wrong && <p>{r.why_your_answer_is_wrong}</p>}
        <p className="muted">{r.explanation}</p>
        {r.check_note && <p className="muted"><small>{r.check_note}</small></p>}
      </li>)}
    </ol>}
    <div className="c4r-actions">
      <button type="button" onClick={onContinue}>Continue <Icon name="arrow" size={14} /></button>
      {onRetry && <button type="button" className="button-secondary" onClick={onRetry}>Open this lesson again</button>}
    </div>
  </div>
}

// ------------------------------------------------------------------ activity (lesson or diagnostic)
function Activity({ assessmentId, request, onDone, onClose }) {
  const [state, setState] = useState({ loading: true, error: '', activity: null, result: null, busy: false })
  const [rubric, setRubric] = useState([])
  const [practicalNote, setPracticalNote] = useState('')

  useEffect(() => {
    let active = true
    setState({ loading: true, error: '', activity: null, result: null, busy: false })
    setRubric([])
    setPracticalNote('')
    openActivity(assessmentId, request)
      .then(activity => { if (active) setState(s => ({ ...s, loading: false, activity })) })
      .catch(error => { if (active) setState(s => ({ ...s, loading: false, error: error.message })) })
    return () => { active = false }
  }, [assessmentId, request])

  async function submit(kind, answers) {
    const { activity } = state
    setState(s => ({ ...s, busy: true, error: '' }))
    try {
      const result = await submitLearningAttempt(assessmentId, {
        skill_id: request.skillId, kind, answers,
        topic_id: kind === 'diagnostic' ? (activity.scope === 'test_out' ? request.topicId : null) : activity.topic_id,
        scope: kind === 'diagnostic' ? activity.scope : null,
      })
      if (kind === 'practical') {
        setPracticalNote(result.decision.message)
        setState(s => ({ ...s, busy: false }))
      } else {
        setState(s => ({ ...s, busy: false, result }))
      }
      onDone(result, kind === 'practical')
    } catch (error) {
      setState(s => ({ ...s, busy: false, error: error.message }))
    }
  }

  if (state.loading) return <div className="c4l-activity" role="status">Preparing your activity…</div>
  if (state.error && !state.activity) return <div className="c4l-activity">
    <p className="error-message" role="alert">{state.error}</p>
    <button type="button" className="button-secondary" onClick={onClose}>Back to my plan</button>
  </div>
  const { activity, result } = state
  const isLesson = activity.kind !== 'diagnostic'
  return <div className="c4l-activity">
    <div className="c4l-activity-head">
      <div>
        <p className="eyebrow">{activity.skill_name} · {isLesson ? `${activity.stage} lesson` : 'Diagnostic'}</p>
        <h3>{isLesson ? activity.title : activity.topics.map(t => t.title).join(' · ')}</h3>
        <div className="c4r-tags">
          {isLesson && <span className="c4r-tag">{activity.mode_label}</span>}
          {isLesson && <span className="c4r-tag">{activity.source}</span>}
          {activity.ai_generated && <span className="c4r-tag is-ai">AI-generated</span>}
        </div>
      </div>
      <button type="button" className="button-secondary" onClick={onClose}>Back to my plan</button>
    </div>
    {(activity.why_now || activity.reason) && <p className="c4r-caution"><Icon name="spark" size={15} />{activity.why_now || activity.reason}</p>}

    {result ? <Feedback result={result} onContinue={onClose}
      onRetry={isLesson && result.decision.case !== 'advance' ? () => setState(s => ({ ...s, result: null })) : null} />
      : <>
        {isLesson && <div className="c4l-lesson">
          {activity.sections.map(section => <Section key={section.kind + section.title} section={section} rubric={rubric}
            onRubric={i => setRubric(r => r.includes(i) ? r.filter(x => x !== i) : [...r, i])} />)}
          <div className="c4r-actions">
            <button type="button" className="button-secondary" disabled={state.busy || rubric.length === 0}
              onClick={() => submit('practical', { rubric })}>Record my self-check</button>
          </div>
          {practicalNote && <p className="c4r-notice" role="status">{practicalNote}</p>}
          {activity.supplementary_resources?.length > 0 && <section className="c4l-part">
            <h4>Extra resources at this level</h4>
            <ul>{activity.supplementary_resources.map(r => <li key={r.url || r.title}>
              {r.url ? <a href={r.url} target="_blank" rel="noreferrer">{r.title}</a> : r.title}
              {r.type && <small className="muted"> · {r.type} · {r.level}</small>}
            </li>)}</ul>
          </section>}
        </div>}
        <h4 className="c4l-quiz-title">{isLesson ? 'Check your understanding' : `${activity.questions.length} quick questions`}</h4>
        {state.error && <p className="error-message" role="alert">{state.error}</p>}
        <QuestionForm key={activity.topic_id || activity.scope} questions={isLesson ? activity.quiz : activity.questions}
          submitLabel={isLesson ? 'Submit quiz' : 'Submit diagnostic'} busy={state.busy}
          onSubmit={answers => submit(isLesson ? 'quiz' : 'diagnostic', answers)} />
      </>}
  </div>
}

// ------------------------------------------------------------------ plan overview
function SkillCard({ skill, ai, onOpen, onGenerate, busy }) {
  return <details className={`c4l-skill status-${skill.status}`} open={['active', 'revision'].includes(skill.status)}>
    <summary>
      <span className="c4l-skill-name"><strong>{skill.skill_name}</strong>
        <small>{skill.entry_stage} → {skill.target_stage}{skill.placement && skill.placement.placed_stage !== skill.entry_stage ? ` · now from ${skill.placement.placed_stage}` : ''}</small>
      </span>
      {skill.progress && <span className="c4l-progress" aria-label={`${skill.progress.done} of ${skill.progress.total} topics done`}>
        <span style={{ width: `${skill.progress.percent}%` }} />
      </span>}
      <span className={`c4l-skill-status status-${skill.status}`}>{SKILL_STATUS[skill.status] || skill.status}</span>
    </summary>
    {skill.message && <p className="muted">{skill.message}</p>}
    {skill.status === 'self_study' && ai.configured && <button type="button" className="button-secondary" disabled={busy}
      onClick={() => onGenerate(skill.skill_id)}>{busy ? 'Creating lessons…' : 'Create AI lessons for this skill'}</button>}
    {skill.placement?.checkpoint && <p className="c4l-note">{skill.placement.reason}
      <button type="button" className="c4l-link" onClick={() => onOpen({ skillId: skill.skill_id, kind: 'diagnostic' })}>Take the diagnostic</button></p>}
    {skill.mismatch === 'confirmed' && <p className="c4l-note">Your diagnostic did not support your high self-rating yet. That is useful: the lessons now start where you need them.</p>}
    {skill.topics.length > 0 && <ol className="c4l-topics">
      {skill.topics.filter(t => t.in_scope).map(t => <li key={t.topic_id} className={TOPIC_STATE[t.state].className}>
        <span><strong>{t.title}</strong><small>{t.stage}{t.best_score != null ? ` · best ${Math.round(t.best_score * 100)}%` : ''}</small></span>
        <span className="c4l-topic-state">{TOPIC_STATE[t.state].label}</span>
        <span className="c4l-topic-actions">
          <button type="button" className="c4l-link" onClick={() => onOpen({ skillId: skill.skill_id, topicId: t.topic_id })}>
            {t.state === 'mastered' ? 'Review' : 'Open lesson'}</button>
          {['not_started', 'learning'].includes(t.state) && !skill.placement?.checkpoint && <button type="button" className="c4l-link"
            onClick={() => onOpen({ skillId: skill.skill_id, topicId: t.topic_id, kind: 'diagnostic', scope: 'test_out' })}>I know this – test me</button>}
        </span>
      </li>)}
    </ol>}
  </details>
}

export default function LearningCoach({ assessmentId, onAnalysis }) {
  const [state, setState] = useState({ loading: true, error: '', plan: null })
  const [request, setRequest] = useState(null)
  const [generating, setGenerating] = useState(null)
  const [reload, setReload] = useState(0)
  const signedIn = hasCvSession()

  useEffect(() => {
    if (!signedIn) { setState({ loading: false, error: '', plan: null }); return undefined }
    let active = true
    getLearningPlan(assessmentId)
      .then(plan => { if (active) setState({ loading: false, error: '', plan }) })
      .catch(error => { if (active) setState({ loading: false, error: error.message, plan: null }) })
    return () => { active = false }
  }, [assessmentId, reload, signedIn])

  function open(next) {
    setRequest({ skillId: next.skillId ?? next.skill_id, topicId: next.topicId ?? next.topic_id ?? undefined,
      kind: next.kind === 'diagnostic' ? 'diagnostic' : 'lesson', scope: next.scope })
  }

  function handleDone(result) {
    if (result.plan) setState(s => ({ ...s, plan: result.plan }))
    if (result.analysis) onAnalysis?.(result.analysis)
  }

  async function handleGenerate(skillId) {
    setGenerating(skillId)
    try {
      const plan = await generateLessons(assessmentId, skillId)
      setState({ loading: false, error: '', plan })
    } catch (error) {
      setState(s => ({ ...s, error: error.message }))   // the current plan stays on screen
    }
    finally { setGenerating(null) }
  }

  const title = <div className="c4r-section-title"><span className="step-number">05</span><h2 id="c4l-title">Your learning coach</h2></div>
  if (!signedIn) return <section className="card c4r-section" aria-labelledby="c4l-title">{title}
    <p className="muted">Upload your CV in Component 01 to use the interactive lessons. Your progress is saved to your own profile.</p>
  </section>
  if (state.loading) return <section className="card c4r-section" aria-labelledby="c4l-title">{title}<p role="status">Loading your lessons…</p></section>
  if (!state.plan) return <section className="card c4r-section" aria-labelledby="c4l-title">{title}
    <p className="error-message" role="alert">{state.error || 'The learning coach is not available.'}</p>
    <button type="button" className="button-secondary" onClick={() => { setState(s => ({ ...s, loading: true })); setReload(v => v + 1) }}>Try again</button>
  </section>

  const { plan } = state
  const next = plan.next_activity
  return <section className="card c4r-section c4l" aria-labelledby="c4l-title">
    {title}
    <p className="muted">Lessons follow your roadmap order and start at your level. Quiz results update your roadmap and readiness score.</p>
    {state.error && <p className="error-message" role="alert">{state.error}</p>}

    {request ? <Activity assessmentId={assessmentId} request={request} onDone={handleDone}
      onClose={() => setRequest(null)} />
      : <>
        <div className="c4l-next">
          <div>
            <p className="eyebrow">{next ? (next.kind === 'diagnostic' ? 'QUICK CHECK FIRST' : next.kind === 'revision' ? 'REVISION' : 'NEXT LESSON') : 'ALL LESSONS DONE'}</p>
            <h3>{plan.message}</h3>
            {next?.reason && <p className="muted">{next.reason}</p>}
          </div>
          {next && <button type="button" onClick={() => open(next)}>{next.kind === 'diagnostic' ? 'Start the check' : 'Start'} <Icon name="arrow" size={14} /></button>}
        </div>
        <div className="c4l-skills">
          {plan.skills.map(skill => <SkillCard key={skill.skill_id} skill={skill} ai={plan.ai} onOpen={open}
            onGenerate={handleGenerate} busy={generating === skill.skill_id} />)}
        </div>
        {plan.events.length > 0 && <details className="c4r-breakdown" open>
          <summary>Why your roadmap changed</summary>
          <ul className="c4l-events">{plan.events.map(e => <li key={`${e.created_at}-${e.kind}-${e.message}`}>
            <small className="muted">{formatDate(e.created_at)}</small> {e.message}
          </li>)}</ul>
        </details>}
        <details className="c4r-breakdown">
          <summary>How the coach decides</summary>
          <p className="muted">{plan.rules.explanation}</p>
          <p className="muted">{plan.ai.configured
            ? `Optional AI lessons are enabled (${plan.ai.provider}, ${plan.ai.model}). They are checked automatically and labelled “AI-generated”.`
            : 'AI lesson generation is not configured on this server, so only the curated lessons are used. Skills without lessons are marked “Self-study”.'}</p>
        </details>
      </>}
  </section>
}
