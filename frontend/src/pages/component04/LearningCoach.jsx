// Owner: Dewmi - Component 04: adaptive learning tutor, shown inside the roadmap steps (RoadmapResults.jsx).
// Flow: next activity -> lesson adapted to the learner -> quiz (answers hidden until submitted) -> feedback and the
// tutor's decision (advance / targeted practice / re-teach / prerequisite) -> the regenerated roadmap and readiness.
import { useEffect, useState } from 'react'
import Icon from '../../components/Icon.jsx'
import { checkExercise, getLearningPlan, hasCvSession, openActivity, submitLearningAttempt } from './assessmentApi.js'
import './LearningCoach.css'

const TOPIC_STATE = {
  not_started: { label: 'Not started', className: '' },
  learning: { label: 'Learning', className: 'is-learning' },
  needs_revision: { label: 'Needs revision', className: 'is-revision' },
  mastered: { label: 'Mastered', className: 'is-mastered' },
  from_evidence: { label: 'Covered by your evidence', className: 'is-evidence' },
}
export const SKILL_STATUS = {
  active: 'Learning now', revision: 'Revision', next: 'Next', upcoming: 'Upcoming', pending: 'Upcoming',
  completed: 'Lessons done', self_study: 'Lessons coming soon',
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

// Lecture-notes headings: the same icon always means the same kind of part.
const PART_ICON = {
  objective: '🎯', watch_first: '▶️', video: '🎬', focus: '🔁', main_idea: '💡', from_zero: '🧠', career: '🌍', explanation: '📖', read_more: '📚',
  visual: '📊', worked_example: '💻', exercises: '🧪', key_ideas: '🔑', memory_trick: '🧩', career_hack: '⚡', mistakes: '⚠️', practice: '✍️',
  practical: '🛠️', challenge: '🚀', summary: '📌', recall: '🧠', next: '➡️',
}

function VideoPlayer({ video, note }) {
  return <div className="c4l-video">
    <div className="c4l-video-frame">
      <iframe src={`https://www.youtube-nocookie.com/embed/${video.youtube_id}`} title={video.title} loading="lazy"
        allow="encrypted-media; picture-in-picture" allowFullScreen referrerPolicy="strict-origin-when-cross-origin" />
    </div>
    <div className="c4r-tags"><span className="c4r-tag">{video.channel}</span>
      {video.minutes ? <span className="c4r-tag">{video.minutes} min</span> : null}</div>
    <p>{video.why}</p>
    <small className="muted">{note}</small>
    <a className="button button-secondary" href={`https://www.youtube.com/watch?v=${video.youtube_id}`} target="_blank" rel="noopener">
      Open on YouTube <Icon name="arrow" size={13} /></a>
  </div>
}

function ResourceCard({ resource, text }) {
  return <div className="c4l-resource-card">
    <div className="c4r-tags"><span className="c4r-tag">{resource.type}</span><span className="c4r-tag">{resource.level}</span>
      {resource.duration_hours ? <span className="c4r-tag">{resource.duration_hours} h</span> : null}</div>
    <strong>{resource.title}</strong>
    {text && <small className="muted">{text}</small>}
    {resource.url && <a className="button button-secondary" href={resource.url} target="_blank" rel="noopener noreferrer">
      Open <Icon name="arrow" size={13} /></a>}
  </div>
}

function RecallItem({ item, index }) {
  const [shown, setShown] = useState(false)
  return <li>
    <p><strong>{index + 1}. {item.q}</strong></p>
    {shown ? <p className="c4l-recall-answer">{item.a}</p>
      : <button type="button" className="c4l-link" onClick={() => setShown(true)}>Show answer</button>}
  </li>
}

// ------------------------------------------------------------------ interactive exercises (practice only)
// The server checks every answer (the browser never receives the answers before an attempt). A wrong answer shows
// only "Not quite" with "Show hint", "Try again" and "Show answer"; the explanation comes with a correct answer or a reveal.
const EXERCISE_LABEL = {
  predict_output: 'Predict the output', fill_blank: 'Fill in the blank', find_bug: 'Find the bug', order_steps: 'Put the lines in order',
}

function Solution({ result }) {
  const answer = result.correct_answer
  return <div className="c4x-solution">
    {Array.isArray(answer)
      ? <><p><strong>Correct order:</strong></p><ol className="c4x-solution-lines">{answer.map(line => <li key={line}><code>{line}</code></li>)}</ol></>
      : <p><strong>Answer:</strong> <code>{answer}</code></p>}
    {result.fixed_line && <p><strong>Fixed line:</strong> <code>{result.fixed_line}</code></p>}
    {result.also_accepted?.length > 0 && <p className="muted">Also accepted: {result.also_accepted.map(a => <code key={a}>{a}</code>)}</p>}
    <p>{result.explanation}</p>
  </div>
}

function Exercise({ exercise, index, onCheck }) {
  const initial = exercise.type === 'order_steps' ? exercise.lines : exercise.type === 'fill_blank' ? '' : null
  const [answer, setAnswer] = useState(initial)
  const [result, setResult] = useState(null)
  const [hint, setHint] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [moveNote, setMoveNote] = useState('')
  const name = `c4x-${exercise.id}`
  const done = result && (result.correct || result.revealed)
  const ready = exercise.type === 'fill_blank' ? answer.trim() !== '' : answer !== null

  async function send(reveal) {
    setBusy(true)
    setError('')
    try { setResult(await onCheck(exercise.id, reveal ? null : answer, reveal)) }
    catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  function change(value) {
    setAnswer(value)
    if (result && !done) setResult(null)                    // editing after "Not quite" starts a new try
  }
  function move(i, step) {
    const lines = [...answer]
    const j = i + step;
    [lines[i], lines[j]] = [lines[j], lines[i]]
    change(lines)
    setMoveNote(`Moved line ${i + 1} to position ${j + 1} of ${lines.length}.`)
  }
  function tryAgain() {
    if (done) setAnswer(initial)                             // practise again from the start
    setResult(null)
    setMoveNote('')
  }

  return <li className="c4x">
    <form onSubmit={event => { event.preventDefault(); if (ready && !busy && !done) send(false) }}>
      <p className="c4x-type">{index + 1}. {EXERCISE_LABEL[exercise.type]}</p>
      <p className="c4x-prompt" id={`${name}-prompt`}>{exercise.prompt}</p>
      {exercise.setup && <details className="c4x-setup">
        <summary>{exercise.language === 'sql' ? 'Show the table data' : 'Show the code that is already given'}</summary>
        <pre className="c4l-code"><code>{exercise.setup}</code></pre>
      </details>}
      {exercise.code && <pre className="c4l-code"><code>{exercise.code}</code></pre>}
      {exercise.expected_output != null && exercise.type !== 'predict_output' &&
        <p className="c4x-expected"><strong>{exercise.type === 'find_bug' ? 'It should print:' : 'When it is right, it prints:'}</strong>{' '}
          <code>{exercise.expected_output}</code></p>}

      {['predict_output', 'find_bug'].includes(exercise.type) && <fieldset className="c4x-choices" aria-labelledby={`${name}-prompt`} disabled={done}>
        <legend className="c4x-legend">{exercise.type === 'find_bug' ? 'Choose the wrong line' : 'Choose the output'}</legend>
        {(exercise.type === 'find_bug' ? exercise.lines : exercise.options).map((text, i) => <label key={i}>
          <input type="radio" name={name} checked={answer === i} onChange={() => change(i)} />
          {exercise.type === 'find_bug' && <span className="c4x-line-no">{i + 1}</span>}
          <code className="c4x-line">{text}</code>
        </label>)}
      </fieldset>}

      {exercise.type === 'fill_blank' && <label className="c4x-blank">Your answer for ____
        <input type="text" value={answer} onChange={event => change(event.target.value)} disabled={done} maxLength={300}
          autoComplete="off" autoCapitalize="off" spellCheck={false} />
      </label>}

      {exercise.type === 'order_steps' && <>
        <p className="c4x-legend" id={`${name}-order`}>Use the arrow buttons to move each line.</p>
        <ol className="c4x-order" aria-labelledby={`${name}-order`}>
          {answer.map((line, i) => <li key={line}>
            <code className="c4x-line">{line}</code>
            <span className="c4x-move">
              <button type="button" className="button-secondary" disabled={i === 0 || done}
                aria-label={`Move line ${i + 1} up`} onClick={() => move(i, -1)}>↑</button>
              <button type="button" className="button-secondary" disabled={i === answer.length - 1 || done}
                aria-label={`Move line ${i + 1} down`} onClick={() => move(i, 1)}>↓</button>
            </span>
          </li>)}
        </ol>
        <p className="c4x-sr" aria-live="polite">{moveNote}</p>
      </>}

      <div className="c4x-actions">
        {!done && <button type="submit" disabled={!ready || busy}>{busy ? 'Checking…' : 'Check'}</button>}
        <button type="button" className="button-secondary" aria-expanded={hint} onClick={() => setHint(h => !h)}>
          {hint ? 'Hide hint' : 'Show hint'}</button>
        {result && <button type="button" className="button-secondary" onClick={tryAgain}>Try again</button>}
        {result && !done && <button type="button" className="button-secondary" disabled={busy} onClick={() => send(true)}>Show answer</button>}
      </div>
      {hint && <p className="c4x-hint">💡 {exercise.hint}</p>}
      <div role="status" aria-live="polite">
        {result && <div className={`c4x-result ${result.correct ? 'is-correct' : result.revealed ? 'is-revealed' : 'is-wrong'}`}>
          <p className="c4x-verdict">{result.correct ? '✅ Correct!' : result.revealed ? '👀 Here is the answer.' : '❌ Not quite.'}
            {!result.correct && !result.revealed && <span> Use the hint, or change your answer and try again.</span>}</p>
          {done && <Solution result={result} />}
        </div>}
      </div>
      {error && <p className="error-message" role="alert">{error}</p>}
    </form>
  </li>
}

function Exercises({ section, onCheck }) {
  return <>
    <ol className="c4x-list">{section.exercises.map((exercise, i) => <Exercise key={exercise.id} exercise={exercise} index={i} onCheck={onCheck} />)}</ol>
    <p className="muted">{section.note}</p>
  </>
}

function Section({ section, rubric, onRubric, onExercise }) {
  const list = items => <ul>{items.map(item => <li key={item}>{item}</li>)}</ul>
  const title = <h4><span className="c4l-part-icon" aria-hidden="true">{PART_ICON[section.kind] || '•'}</span>{section.title}</h4>
  if (section.kind === 'from_zero') return <details className="c4l-part c4l-part-from_zero" open={!section.collapsed}>
    <summary>{title}{section.collapsed && <small className="muted"> (you can skip this: fast-track version)</small>}</summary>
    {section.text && <p>{section.text}</p>}
    {section.items?.length > 0 && <><p className="c4l-sub">Step by step</p><ol>{section.items.map(item => <li key={item}>{item}</li>)}</ol></>}
  </details>
  return <section className={`c4l-part c4l-part-${section.kind}`}>
    {title}
    {section.text && !['watch_first', 'read_more'].includes(section.kind) && <p>{section.text}</p>}
    {['watch_first', 'read_more'].includes(section.kind) && <ResourceCard resource={section.resource} text={section.text} />}
    {section.kind === 'video' && <VideoPlayer video={section.video} note={section.note} />}
    {section.kind === 'steps' && <ol>{section.items.map(item => <li key={item}>{item}</li>)}</ol>}
    {['focus', 'key_ideas', 'mistakes'].includes(section.kind) && list(section.items)}
    {section.kind === 'visual' && <Visual visual={section.visual} />}
    {section.kind === 'worked_example' && <>
      <pre className="c4l-code"><code>{section.example.code}</code></pre>
      <ol>{section.example.steps.map(step => <li key={step}>{step}</li>)}</ol>
    </>}
    {section.kind === 'exercises' && <Exercises section={section} onCheck={onExercise} />}
    {section.kind === 'recall' && <><ol className="c4l-recall">{section.recall.map((item, i) => <RecallItem key={item.q} item={item} index={i} />)}</ol>
      <p className="muted">{section.note}</p></>}
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

const QUESTION_LEVEL = ['Quick check', 'Apply it', 'Think deeper']

function Question({ q, index, value, onChange, levels }) {
  const name = `c4l-${q.id}`
  return <fieldset className="c4l-question" aria-labelledby={`${name}-prompt`}>
    {levels && <span className="c4l-q-level">Q{index + 1} · {QUESTION_LEVEL[index] || 'Practice'}{q.type === 'short' ? ' · write your answer' : ''}</span>}
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

function QuestionForm({ questions, submitLabel, busy, onSubmit, levels = false }) {
  const [answers, setAnswers] = useState({})
  const answered = questions.filter(q => answers[q.id] !== undefined && answers[q.id] !== '' &&
    !(Array.isArray(answers[q.id]) && answers[q.id].length === 0)).length
  return <form className="c4l-quiz" onSubmit={event => { event.preventDefault(); onSubmit(answers) }}>
    {questions.map((q, i) => <Question key={q.id} q={q} index={i} value={answers[q.id]} levels={levels}
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
export function Activity({ assessmentId, request, onDone, onClose }) {
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
    <button type="button" className="button-secondary" onClick={onClose}>Back to my roadmap</button>
  </div>
  const { activity, result } = state
  const isLesson = activity.kind !== 'diagnostic'
  return <div className="c4l-activity">
    <div className="c4l-activity-head">
      <div>
        <p className="eyebrow">{activity.skill_name} · {isLesson ? `Topic ${activity.topic_number} of ${activity.topic_total} · ${activity.stage}` : 'Quick check'}</p>
        <h3>{isLesson ? activity.title : activity.topics.map(t => t.title).join(' · ')}</h3>
        <div className="c4r-tags">
          {isLesson && <span className="c4r-tag">{activity.mode_label}</span>}
          {isLesson && <span className="c4r-tag">{activity.source}</span>}
          {activity.ai_generated && <span className="c4r-tag is-ai">AI-generated</span>}
        </div>
      </div>
      <button type="button" className="button-secondary" onClick={onClose}>Back to my roadmap</button>
    </div>
    {(activity.why_now || activity.reason) && <p className="c4r-caution"><Icon name="spark" size={15} />{activity.why_now || activity.reason}</p>}
    {isLesson && activity.personalised?.length > 0 && !result && <div className="c4l-arranged">
      <strong>✨ Arranged for you</strong>
      <ul>{activity.personalised.map(note => <li key={note}>{note}</li>)}</ul>
    </div>}

    {result ? <Feedback result={result} onContinue={onClose}
      onRetry={isLesson && result.decision.case !== 'advance' ? () => setState(s => ({ ...s, result: null })) : null} />
      : <>
        {isLesson && <div className="c4l-lesson">
          {activity.sections.filter(x => x.kind !== 'next').map(section => <Section key={section.kind + section.title} section={section} rubric={rubric}
            onRubric={i => setRubric(r => r.includes(i) ? r.filter(x => x !== i) : [...r, i])}
            onExercise={(exerciseId, answer, reveal) => checkExercise(assessmentId,
              { skillId: request.skillId, topicId: activity.topic_id, exerciseId, answer, reveal })} />)}
          <div className="c4r-actions">
            <button type="button" className="button-secondary" disabled={state.busy || rubric.length === 0}
              onClick={() => submit('practical', { rubric })}>Record my self-check</button>
          </div>
          {practicalNote && <p className="c4r-notice" role="status">{practicalNote}</p>}
          {activity.supplementary_resources?.length > 0 && <section className="c4l-part">
            <h4><span className="c4l-part-icon" aria-hidden="true">🔗</span>More resources at this level</h4>
            <ul>{activity.supplementary_resources.map(r => <li key={r.url || r.title}>
              {r.url ? <a href={r.url} target="_blank" rel="noreferrer">{r.title}</a> : r.title}
              {r.type && <small className="muted"> · {r.type} · {r.level}</small>}
            </li>)}</ul>
          </section>}
        </div>}
        <h4 className="c4l-quiz-title">{isLesson ? '❓ Practice questions' : `${activity.questions.length} quick questions`}</h4>
        {isLesson && <p className="muted c4l-quiz-note">Answers and explanations appear after you submit. 80% or more marks this topic as mastered.</p>}
        {state.error && <p className="error-message" role="alert">{state.error}</p>}
        <QuestionForm key={activity.topic_id || activity.scope} questions={isLesson ? activity.quiz : activity.questions}
          submitLabel={isLesson ? 'Submit quiz' : 'Submit diagnostic'} busy={state.busy} levels={isLesson}
          onSubmit={answers => submit(isLesson ? 'quiz' : 'diagnostic', answers)} />
        {isLesson && activity.sections.filter(x => x.kind === 'next').map(section => <Section key="next" section={section} rubric={rubric} onRubric={() => {}} />)}
      </>}
  </div>
}

// ------------------------------------------------------------------ pieces used by the roadmap page
// The learning plan (per-skill placement, topics, locks, next activity, events). Kept while it refreshes.
export function useLearningPlan(assessmentId, version = 0) {
  const signedIn = hasCvSession()
  const [state, setState] = useState({ loading: signedIn, error: '', plan: null })
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    if (!signedIn) { setState({ loading: false, error: '', plan: null }); return undefined }
    let active = true
    setState(s => ({ ...s, loading: true }))
    getLearningPlan(assessmentId)
      .then(plan => { if (active) setState({ loading: false, error: '', plan }) })
      .catch(error => { if (active) setState(s => ({ loading: false, error: error.message, plan: s.plan })) })
    return () => { active = false }
  }, [assessmentId, version, retry, signedIn])

  return { ...state, signedIn, setPlan: plan => setState({ loading: false, error: '', plan }),
    setError: error => setState(s => ({ ...s, error })), reload: () => setRetry(v => v + 1) }
}

// {skill_id: lessons view} for joining the plan to the roadmap steps.
export const lessonsBySkill = plan => Object.fromEntries((plan?.skills || []).map(s => [s.skill_id, s]))

// Lesson progress over every roadmap skill that has lessons.
export function lessonTotals(plan) {
  const skills = (plan?.skills || []).filter(s => s.progress)
  const done = skills.reduce((n, s) => n + s.progress.done, 0)
  const total = skills.reduce((n, s) => n + s.progress.total, 0)
  return { done, total, percent: total ? Math.round(100 * done / total) : 0, skills: skills.length }
}

export function NextActivityCard({ plan, onOpen, compact = false }) {
  const next = plan?.next_activity
  return <div className={`c4l-next ${compact ? 'is-compact' : ''}`}>
    <div>
      <p className="eyebrow">{next ? (next.kind === 'diagnostic' ? 'QUICK CHECK FIRST' : next.kind === 'revision' ? 'REVISION' : 'CONTINUE LEARNING') : 'ALL LESSONS DONE'}</p>
      <h3>{plan.message}</h3>
      {next?.reason && <p className="muted">{next.reason}</p>}
    </div>
    {next && <button type="button" onClick={() => onOpen(next)}>{next.kind === 'diagnostic' ? 'Start the check' : 'Continue'} <Icon name="arrow" size={14} /></button>}
  </div>
}

// Lessons of one roadmap skill: placement check, topic list with locks, or the "coming soon" note.
export function SkillLessons({ skill, ai, onOpen, onGenerate, busy }) {
  if (!skill) return null
  if (skill.status === 'self_study') return <div className="c4l-lessons is-empty">
    <h4>Lessons</h4>
    <p className="muted">Interactive lessons for {skill.skill_name} are coming soon. Until then, learn with the resources and the
      practical project below; your progress is confirmed when your updated CV (Component 01) shows the skill.</p>
    {ai.configured && <button type="button" className="button-secondary" disabled={busy}
      onClick={() => onGenerate(skill.skill_id)}>{busy ? 'Creating lessons…' : 'Create AI lessons for this skill'}</button>}
  </div>
  return <div className="c4l-lessons">
    <div className="c4l-lessons-head">
      <h4>📚 Lesson roadmap</h4>
      {skill.progress && <span className="c4l-progress-text">{skill.progress.done}/{skill.progress.total} done</span>}
    </div>
    {skill.placement?.checkpoint && <p className="c4l-note">{skill.placement.reason}
      <button type="button" className="c4l-link" onClick={() => onOpen({ skillId: skill.skill_id, kind: 'diagnostic' })}>Take the quick check</button></p>}
    {skill.mismatch === 'confirmed' && <p className="c4l-note">Your quick check did not support your high self-rating yet. That is useful: the lessons now start where you need them.</p>}
    {skill.status === 'completed' && <p className="c4l-note is-done">{skill.message}</p>}
    <ol className="c4l-topics">
      {skill.topics.filter(t => t.in_scope).map(t => <li key={t.topic_id}
        className={`${TOPIC_STATE[t.state].className} ${t.locked ? 'is-locked' : ''}`}>
        <span><strong>{t.locked && <span className="c4l-lock" aria-hidden="true">🔒 </span>}{t.title}</strong>
          <small>{t.stage}{t.best_score != null ? ` · best ${Math.round(t.best_score * 100)}%` : ''}</small>
          {t.objective && <small className="c4l-objective">{t.objective}</small>}</span>
        <span className="c4l-topic-state">{t.locked ? 'Locked' : TOPIC_STATE[t.state].label}</span>
        <span className="c4l-topic-actions">
          {t.locked ? <small className="c4l-lock-reason">{t.lock_reason}</small> : <>
            <button type="button" className="c4l-link" onClick={() => onOpen({ skillId: skill.skill_id, topicId: t.topic_id })}>
              {t.state === 'mastered' ? 'Review' : 'Open lesson'}</button>
            {['not_started', 'learning'].includes(t.state) && <button type="button" className="c4l-link"
              onClick={() => onOpen({ skillId: skill.skill_id, topicId: t.topic_id, kind: 'diagnostic', scope: 'test_out' })}>I know this – test me</button>}
          </>}
        </span>
      </li>)}
    </ol>
  </div>
}

export function RoadmapEvents({ events }) {
  if (!events?.length) return <p className="muted">No changes yet. Your roadmap updates when you pass lessons and quizzes, add proof, or upload an updated CV.</p>
  return <ul className="c4l-events">{events.map(e => <li key={`${e.created_at}-${e.kind}-${e.message}`}>
    <small className="muted">{formatDate(e.created_at)}</small> {e.message}
  </li>)}</ul>
}

export function CoachRules({ plan }) {
  return <details className="c4r-breakdown">
    <summary>How the coach decides</summary>
    <p className="muted">{plan.rules.explanation}</p>
    <p className="muted">{plan.ai.configured
      ? `Optional AI lessons are enabled (${plan.ai.provider}, ${plan.ai.model}). They are checked automatically and labelled “AI-generated”.`
      : 'AI lesson generation is not configured on this server, so only the curated lessons are used.'}</p>
  </details>
}

// Turns a "next activity" or a topic click into an activity request.
export const activityRequest = next => ({ skillId: next.skillId ?? next.skill_id, topicId: next.topicId ?? next.topic_id ?? undefined,
  kind: next.kind === 'diagnostic' ? 'diagnostic' : 'lesson', scope: next.scope })
