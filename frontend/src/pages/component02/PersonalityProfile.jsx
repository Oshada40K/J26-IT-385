import { useEffect, useState } from 'react'
import Icon from '../../components/Icon.jsx'
import { analyseTextAnswers, getQuestionnaire, scoreQuestionnaire } from './personalityApi.js'
import './PersonalityProfile.css'

const MIN_WORDS = 20 // the backend rejects shorter text
const PAGE_SIZE = 13
const DRAFT_KEY = 'careernova-personality-draft'

const QUESTIONS = [
  { id: 'problem', label: 'Problem solving', prompt: 'Describe how you usually approach a difficult problem in your studies or a project.' },
  { id: 'team', label: 'Teamwork', prompt: 'How do you work with others in a team? What role do you usually take?' },
  { id: 'challenge', label: 'Handling challenges', prompt: 'Tell us about a time something went wrong or you faced a setback. How did you react?' },
  { id: 'learning', label: 'Learning style', prompt: 'How do you prefer to learn something completely new to you?' },
]

const TRAITS = [
  { code: 'OPN', name: 'Openness', high: 'Curious, imaginative, enjoys new ideas', low: 'Practical, prefers the familiar' },
  { code: 'CON', name: 'Conscientiousness', high: 'Organised, plans ahead, dependable', low: 'Flexible, spontaneous' },
  { code: 'EXT', name: 'Extraversion', high: 'Energised by people and social settings', low: 'Reserved, prefers focused solo work' },
  { code: 'AGR', name: 'Agreeableness', high: 'Cooperative, empathetic, trusting', low: 'Direct, competitive, sceptical' },
  { code: 'NEU', name: 'Neuroticism', high: 'Feels stress and worry more easily', low: 'Calm and steady under pressure' },
]

const STAGES = [
  { id: 'questionnaire', name: 'Big Five questionnaire', detail: '50 statements about how you see yourself', ready: true },
  { id: 'writing', name: 'Behavioural answers', detail: 'Short written answers about how you work', ready: true },
  { id: 'sjt', name: 'Situational judgement', detail: 'Realistic workplace scenarios', ready: false },
]

const countWords = text => text.trim().split(/\s+/).filter(Boolean).length

function loadDraft() {
  try { return JSON.parse(sessionStorage.getItem(DRAFT_KEY) || 'null') || {} }
  catch { return {} }
}

function saveDraft(draft) {
  try { sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft)) }
  catch { /* storage unavailable: the page still works without a saved draft */ }
}

// Questionnaire scores are trait levels; only describe the person when the level is clearly high or low.
function describe(trait, level) {
  if (level >= 0.6) return trait.high
  if (level <= 0.4) return trait.low
  return 'Balanced between both ends'
}

function leaning(p) {
  if (Math.abs(p - 0.5) < 0.1) return 'Unclear'
  return p >= 0.5 ? 'Leans high' : 'Leans low'
}

function Meter({ value, label, variant }) {
  const percent = Math.round(value * 100)
  return <div className={`personality-meter personality-meter-${variant}`} role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
    <span className="personality-meter-fill" style={{ width: `${percent}%` }} />
    <span className="personality-meter-mid" aria-hidden="true" />
  </div>
}

function TraitRow({ trait, level, writing }) {
  return <div className="personality-trait">
    <div className="personality-trait-heading">
      <div><h3>{trait.name}</h3>{level != null && <small>{describe(trait, level)}</small>}</div>
    </div>
    {level != null && <div className="personality-source">
      <span>Your answers</span>
      <Meter value={level} variant="questionnaire" label={`${trait.name} from questionnaire: ${Math.round(level * 100)} out of 100`} />
      <strong>{Math.round(level * 100)}<small className="is-inline">/100</small></strong>
    </div>}
    {writing != null && <div className="personality-source">
      <span>Your writing</span>
      <Meter value={writing} variant="writing" label={`${trait.name} from writing: ${Math.round(writing * 100)}% likely high`} />
      <strong>{Math.round(writing * 100)}%<small>{leaning(writing)}</small></strong>
    </div>}
  </div>
}

function Questionnaire({ answers, onAnswer, onScored }) {
  const [data, setData] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getQuestionnaire().then(d => { if (active) setData(d) }).catch(err => { if (active) setLoadError(err.message) })
    return () => { active = false }
  }, [])

  if (loadError) return <div className="card"><p className="error-message" role="alert">{loadError}</p></div>
  if (!data) return <div className="card" role="status">Loading the questionnaire…</div>

  const pages = Math.ceil(data.items.length / PAGE_SIZE)
  const shown = data.items.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const answered = data.items.filter(i => answers[i.id]).length
  const pageDone = shown.every(i => answers[i.id])
  const allDone = answered === data.items.length

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try { onScored(await scoreQuestionnaire(answers)) }
    catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  function goTo(next) {
    setPage(next)
    document.getElementById('personality-stage')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return <form className="card personality-form" onSubmit={submit}>
    <h2>Big Five questionnaire</h2>
    <p className="muted">How well does each statement describe you as you generally are now, not as you wish to be? There are no right or wrong answers.</p>
    <div className="personality-progress" aria-label={`${answered} of ${data.items.length} answered`}>
      <span style={{ width: `${(answered / data.items.length) * 100}%` }} />
    </div>
    <p className="personality-progress-label muted">Page {page + 1} of {pages} · {answered} of {data.items.length} answered</p>
    {shown.map((item, i) => <fieldset key={item.id} className="personality-likert">
      <legend><span className="personality-likert-number">{page * PAGE_SIZE + i + 1}</span>{item.text}</legend>
      <div className="personality-likert-options">
        {data.scale_labels.map((label, index) => <label key={label} className={answers[item.id] === index + 1 ? 'is-selected' : ''}>
          <input type="radio" name={item.id} value={index + 1} checked={answers[item.id] === index + 1} onChange={() => onAnswer(item.id, index + 1)} disabled={loading} />
          {label}
        </label>)}
      </div>
    </fieldset>)}
    <div className="personality-submit">
      <button type="button" className="button-secondary" onClick={() => goTo(page - 1)} disabled={page === 0 || loading}>Back</button>
      {page < pages - 1
        ? <button type="button" onClick={() => goTo(page + 1)} disabled={!pageDone}>Next page <Icon name="arrow" size={16} /></button>
        : <button type="submit" className="button-ai" disabled={!allDone || loading}>{loading ? 'Scoring…' : <>Score my answers <Icon name="spark" size={16} /></>}</button>}
    </div>
    {!pageDone && <p className="personality-hint">Answer every statement on this page to continue.</p>}
    {error && <p className="error-message" role="alert">{error}</p>}
  </form>
}

function Writing({ answers, onAnswer, onScored }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const totalWords = QUESTIONS.reduce((sum, q) => sum + countWords(answers[q.id] || ''), 0)

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try { onScored(await analyseTextAnswers(QUESTIONS.map(q => answers[q.id] || '').filter(a => a.trim()))) }
    catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  return <form className="card personality-form" onSubmit={submit}>
    <h2>Behavioural answers</h2>
    <p className="muted">Answer in your own words with real examples. There are no right or wrong answers. Aim for 80–150 words per question.</p>
    {QUESTIONS.map((q, i) => <label key={q.id} className="personality-question">
      <span className="personality-question-label"><span className="step-number">0{i + 1}</span>{q.label}</span>
      <span className="personality-question-prompt">{q.prompt}</span>
      <textarea rows={4} value={answers[q.id] || ''} disabled={loading} onChange={e => onAnswer(q.id, e.target.value)} />
      <small className="muted">{countWords(answers[q.id] || '')} words</small>
    </label>)}
    <div className="personality-submit">
      <span className={totalWords >= MIN_WORDS ? 'muted' : 'personality-hint'}>{totalWords} words in total{totalWords < MIN_WORDS && ` · at least ${MIN_WORDS} needed`}</span>
      <button type="submit" className="button-ai" disabled={totalWords < MIN_WORDS || loading}>{loading ? 'Analysing…' : <>Analyse my answers <Icon name="spark" size={16} /></>}</button>
    </div>
    {loading && <p className="muted" role="status">The first analysis can take up to a minute while the language model loads.</p>}
    {error && <p className="error-message" role="alert">{error}</p>}
  </form>
}

export default function PersonalityProfile() {
  const [draft, setDraft] = useState(() => ({ stage: 'questionnaire', likert: {}, text: {}, questionnaire: null, writing: null, ...loadDraft() }))
  useEffect(() => saveDraft(draft), [draft])
  const update = patch => setDraft(prev => ({ ...prev, ...patch }))

  const { questionnaire, writing } = draft
  const hasResults = questionnaire || writing

  return <div className="page accent-personality">
    <div className="page-heading">
      <div><p className="eyebrow">COMPONENT 02 / CAREER INTELLIGENCE</p><h1>Discover your work personality</h1><p className="page-description">Understand your personality traits, behavioural patterns and decision-making style to find careers that fit you.</p></div>
      <span className="component-icon"><Icon name="personality" size={28} /></span>
    </div>

    <nav className="card personality-stages" aria-label="Assessment stages" id="personality-stage">
      {STAGES.map((stage, i) => {
        const done = (stage.id === 'questionnaire' && questionnaire) || (stage.id === 'writing' && writing)
        return <button key={stage.id} type="button" disabled={!stage.ready} aria-current={draft.stage === stage.id ? 'step' : undefined}
          className={draft.stage === stage.id ? 'is-active' : ''} onClick={() => update({ stage: stage.id })}>
          <span className="step-number">0{i + 1}</span>
          <span><strong>{stage.name}</strong><small>{stage.detail}</small></span>
          <span className={`status ${done ? 'status-ai' : 'status-neutral'}`}>{!stage.ready ? 'Coming soon' : done ? <><Icon name="check" size={13} /> Done</> : 'To do'}</span>
        </button>
      })}
    </nav>

    <div className="personality-layout">
      {draft.stage === 'writing'
        ? <Writing answers={draft.text} onAnswer={(id, v) => setDraft(prev => ({ ...prev, text: { ...prev.text, [id]: v } }))} onScored={r => update({ writing: r })} />
        : <Questionnaire answers={draft.likert} onAnswer={(id, v) => setDraft(prev => ({ ...prev, likert: { ...prev.likert, [id]: v } }))} onScored={r => update({ questionnaire: r })} />}

      <section className="card personality-results" aria-live="polite">
        <h2>Your profile so far</h2>
        {!hasResults ? <div className="personality-empty">
          <span className="component-icon"><Icon name="pulse" size={24} /></span>
          <p className="muted">Complete the questionnaire or the written answers to see your Big Five profile here.</p>
        </div> : <>
          <div className="personality-legend">
            {questionnaire && <span><i className="personality-key-questionnaire" />Your answers · questionnaire</span>}
            {writing && <span><i className="personality-key-writing" />Your writing · <span className="personality-badge">Text-only · low reliability</span></span>}
          </div>
          {questionnaire?.warnings?.map(w => <p key={w} className="personality-warning" role="alert">{w}</p>)}
          {TRAITS.map(trait => <TraitRow key={trait.code} trait={trait} level={questionnaire?.traits[trait.code]} writing={writing?.traits[trait.code]} />)}
          <p className="personality-note"><Icon name="check" size={15} />
            {questionnaire && writing
              ? 'The two sources measure your traits in different ways. Where they disagree a lot, the consistency check (coming next) will flag that trait for a closer look.'
              : questionnaire
                ? 'This profile is from the questionnaire only. Add your written answers so they can be compared.'
                : 'The writing estimate alone is not reliable. Complete the questionnaire to build your profile.'}
          </p>
        </>}
      </section>
    </div>
  </div>
}
