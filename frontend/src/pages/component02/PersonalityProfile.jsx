import { useEffect, useState } from 'react'
import Icon from '../../components/Icon.jsx'
import { analyseTextAnswers, assessProfile, getQuestionnaire, getScenarios, scoreQuestionnaire, scoreScenarios } from './personalityApi.js'
import './PersonalityProfile.css'

const MIN_WORDS = 20 // the backend rejects shorter text
const MAX_PAGE_SIZE = 8 // pages are balanced, so 52 statements become 7 pages of 7-8
const DRAFT_KEY = 'careernova-personality-draft'

const QUESTIONS = [
  { id: 'problem', label: 'Problem solving', prompt: 'Describe how you usually approach a difficult problem in your studies or a project.' },
  { id: 'team', label: 'Teamwork', prompt: 'How do you work with others in a team? What role do you usually take?' },
  { id: 'challenge', label: 'Handling challenges', prompt: 'Tell us about a time something went wrong or you faced a setback. How did you react?' },
  { id: 'learning', label: 'Learning style', prompt: 'How do you prefer to learn something completely new to you?' },
]

const TRAITS = [
  { code: 'OPN', name: 'Openness', high: 'Curious, imaginative, enjoys new ideas', low: 'Practical, prefers the familiar', more: 'open to new ideas' },
  { code: 'CON', name: 'Conscientiousness', high: 'Organised, plans ahead, dependable', low: 'Flexible, spontaneous', more: 'organised and dependable' },
  { code: 'EXT', name: 'Extraversion', high: 'Energised by people and social settings', low: 'Reserved, prefers focused solo work', more: 'outgoing' },
  { code: 'AGR', name: 'Agreeableness', high: 'Cooperative, empathetic, trusting', low: 'Direct, competitive, sceptical', more: 'cooperative and caring' },
  { code: 'NEU', name: 'Neuroticism', high: 'Feels stress and worry more easily', low: 'Calm and steady under pressure', more: 'easily stressed' },
]

const STAGES = [
  { id: 'questionnaire', name: 'Big Five questionnaire', detail: '52 statements (2 attention checks) · about 6 minutes', ready: true },
  { id: 'writing', name: 'Behavioural answers', detail: 'Short written answers about how you work', ready: true },
  { id: 'sjt', name: 'Situational judgement', detail: 'Realistic workplace scenarios', ready: true },
  { id: 'final', name: 'Your profile', detail: 'Combined result and consistency', ready: true },
]

const SOURCE_LABELS = { questionnaire: 'Questionnaire', situational_judgement: 'Scenarios', text: 'Writing' }

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

function TraitRow({ trait, level, choices, writing }) {
  return <div className="personality-trait">
    <div className="personality-trait-heading">
      <div><h3>{trait.name}</h3>{level != null && <small>{describe(trait, level)}</small>}</div>
    </div>
    {level != null && <div className="personality-source">
      <span>Your answers</span>
      <Meter value={level} variant="questionnaire" label={`${trait.name} from questionnaire: ${Math.round(level * 100)} out of 100`} />
      <strong>{Math.round(level * 100)}<small className="is-inline">/100</small></strong>
    </div>}
    {choices != null && <div className="personality-source">
      <span>Your choices</span>
      <Meter value={choices} variant="sjt" label={`${trait.name} from scenario choices: ${Math.round(choices * 100)} out of 100`} />
      <strong>{Math.round(choices * 100)}<small className="is-inline">/100</small></strong>
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

  const pages = Math.ceil(data.items.length / MAX_PAGE_SIZE)
  const pageStart = n => Math.round(n * data.items.length / pages)
  const shown = data.items.slice(pageStart(page), pageStart(page + 1))
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

  // On a first answer, bring the next unanswered statement (or the page buttons) into view.
  // Changing an earlier answer does not move the page.
  function choose(id, value) {
    const first = !answers[id]
    onAnswer(id, value)
    if (!first) return
    const rest = shown.slice(shown.findIndex(i => i.id === id) + 1)
    const target = rest.find(i => !answers[i.id])
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    requestAnimationFrame(() => document.getElementById(target ? `likert-${target.id}` : 'personality-questionnaire-actions')
      ?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'center' }))
  }

  return <form className="card personality-form" onSubmit={submit}>
    <h2>Big Five questionnaire</h2>
    <p className="personality-duration">About 6 minutes · {data.items.length} statements</p>
    <p className="muted">How well does each statement describe you as you generally are now, not as you wish to be? There are no right or wrong answers. Two statements are attention checks that tell you exactly which answer to pick.</p>
    <div className="personality-progress" aria-label={`${answered} of ${data.items.length} answered`}>
      <span style={{ width: `${(answered / data.items.length) * 100}%` }} />
    </div>
    <p className="personality-progress-label muted">Page {page + 1} of {pages} · {answered} of {data.items.length} answered</p>
    {shown.map((item, i) => <fieldset key={item.id} id={`likert-${item.id}`} className="personality-likert">
      <legend><span className="personality-likert-number">{pageStart(page) + i + 1}</span>{item.text}</legend>
      <div className="personality-likert-options">
        {data.scale_labels.map((label, index) => <label key={label} className={answers[item.id] === index + 1 ? 'is-selected' : ''}>
          <input type="radio" name={item.id} value={index + 1} checked={answers[item.id] === index + 1} onChange={() => choose(item.id, index + 1)} disabled={loading} />
          {label}
        </label>)}
      </div>
    </fieldset>)}
    <div className="personality-submit" id="personality-questionnaire-actions">
      <button type="button" className="button-secondary" onClick={() => goTo(page - 1)} disabled={page === 0 || loading}>Back</button>
      {page < pages - 1
        ? <button type="button" onClick={() => goTo(page + 1)} disabled={!pageDone}>Next page <Icon name="arrow" size={16} /></button>
        : <button type="submit" className="button-ai" disabled={!allDone || loading}>{loading ? 'Scoring…' : <>Score my answers <Icon name="spark" size={16} /></>}</button>}
    </div>
    {!pageDone && <p className="personality-hint">Answer every statement on this page to continue.</p>}
    {error && <p className="error-message" role="alert">{error}</p>}
  </form>
}

function Scenarios({ answers, onAnswer, onScored }) {
  const [data, setData] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getScenarios().then(d => { if (active) setData(d) }).catch(err => { if (active) setLoadError(err.message) })
    return () => { active = false }
  }, [])

  if (loadError) return <div className="card"><p className="error-message" role="alert">{loadError}</p></div>
  if (!data) return <div className="card" role="status">Loading the scenarios…</div>

  const answered = data.scenarios.filter(s => answers[s.id]).length
  const allDone = answered === data.scenarios.length

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try { onScored(await scoreScenarios(answers)) }
    catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  return <form className="card personality-form" onSubmit={submit}>
    <h2>Situational judgement</h2>
    <p className="muted">{data.instruction}</p>
    <div className="personality-progress" aria-label={`${answered} of ${data.scenarios.length} answered`}>
      <span style={{ width: `${(answered / data.scenarios.length) * 100}%` }} />
    </div>
    <p className="personality-progress-label muted">{answered} of {data.scenarios.length} scenarios answered</p>
    {data.scenarios.map((s, i) => <fieldset key={s.id} className="personality-scenario">
      <legend><span className="step-number">{String(i + 1).padStart(2, '0')}</span><span><small>{s.topic}</small>{s.text}</span></legend>
      <div className="personality-scenario-options">
        {s.options.map(o => <label key={o.id} className={answers[s.id] === o.id ? 'is-selected' : ''}>
          <input type="radio" name={s.id} value={o.id} checked={answers[s.id] === o.id} onChange={() => onAnswer(s.id, o.id)} disabled={loading} />
          <span className="personality-option-letter" aria-hidden="true">{o.id}</span>
          <span>{o.text}</span>
        </label>)}
      </div>
    </fieldset>)}
    <div className="personality-submit">
      <span className={allDone ? 'muted' : 'personality-hint'}>{allDone ? 'All scenarios answered' : `${data.scenarios.length - answered} scenarios left`}</span>
      <button type="submit" className="button-ai" disabled={!allDone || loading}>{loading ? 'Scoring…' : <>Score my choices <Icon name="spark" size={16} /></>}</button>
    </div>
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

function FinalProfile({ draft }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    // Only send the parts that were completed and scored.
    const texts = QUESTIONS.map(q => draft.text[q.id] || '').filter(a => a.trim())
    assessProfile({
      questionnaire: draft.questionnaire ? draft.likert : null,
      sjt: draft.sjt ? draft.choices : null,
      answers: draft.writing ? texts : null,
    }).then(r => { if (active) setResult(r) })
      .catch(err => { if (active) setError(err.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [draft.questionnaire, draft.sjt, draft.writing, reload])

  if (loading) return <div className="card" role="status">Combining your answers, choices and writing…</div>
  if (error) return <div className="card"><p className="error-message" role="alert">{error}</p><button onClick={() => setReload(v => v + 1)}>Try again</button></div>

  const c = result.consistency
  const used = Object.keys(result.sources).map(s => SOURCE_LABELS[s]).join(', ')
  return <div className="personality-final">
    <section className="card personality-pcs">
      <div>
        <p className="eyebrow">PERSONALITY CONSISTENCY SCORE</p>
        {c ? <>
          <div className="personality-pcs-score"><strong>{Math.round(c.score * 100)}</strong><span>/100</span><span className={`personality-band personality-band-${c.band.label.toLowerCase()}`}>{c.band.label}</span></div>
          <p>{c.band.meaning}</p>
          {c.flagged_traits.length
            ? <p className="muted">Traits to discuss: <strong>{c.flagged_traits.map(t => TRAITS.find(x => x.code === t).name).join(', ')}</strong></p>
            : <p className="muted">No trait shows a large difference between your sources.</p>}
        </> : <p className="muted">Complete the questionnaire and at least one of the other two parts to get a consistency score.</p>}
      </div>
      <dl className="personality-pcs-meta">
        <div><dt>Based on</dt><dd>{used}</dd></div>
        {c && <div><dt>Flag threshold</dt><dd>difference ≥ {Math.round(c.threshold * 100)}</dd></div>}
        <div><dt>Method</dt><dd>Confidence-weighted fusion v{result.fusion_version}</dd></div>
      </dl>
    </section>

    <section className="card">
      <h2>Your combined Big Five profile</h2>
      <p className="muted">Each trait combines how you describe yourself with how you responded in scenarios and writing, weighted by how reliable each part is.</p>
      {TRAITS.map(trait => {
        const value = result.traits[trait.code]
        const pt = c?.per_trait[trait.code]
        return <div key={trait.code} className={`personality-trait personality-final-trait ${pt?.flagged ? 'is-flagged' : ''}`}>
          <div className="personality-trait-heading">
            <div><h3>{trait.name} {pt?.flagged && <span className="personality-flag">Sources disagree</span>}</h3><small>{describe(trait, value)}</small></div>
          </div>
          <div className="personality-source">
            <span>Combined</span>
            <Meter value={value} variant="questionnaire" label={`${trait.name} combined: ${Math.round(value * 100)} out of 100`} />
            <strong>{Math.round(value * 100)}<small className="is-inline">/100</small></strong>
          </div>
          {pt && <p className="personality-final-detail">
            You rated yourself <strong>{Math.round(pt.questionnaire * 100)}</strong>; your scenarios and writing suggest <strong>{Math.round(pt.behavioural * 100)}</strong>
            {' '}(difference {Math.round(pt.divergence * 100)}).
            {pt.flagged && <> {pt.direction === 'self-report higher'
              ? `You describe yourself as more ${trait.more} than your responses show.`
              : `Your responses show you as more ${trait.more} than you describe yourself.`}</>}
          </p>}
        </div>
      })}
      {result.notes.map(n => <p key={n} className="personality-warning">{n}</p>)}
      <div className="personality-final-actions">
        <button type="button" className="button-secondary" onClick={() => setReload(v => v + 1)}>Recalculate</button>
      </div>
      <details className="personality-json">
        <summary>Profile JSON sent to career prediction (Component 3)</summary>
        <pre>{JSON.stringify(result, null, 2)}</pre>
      </details>
    </section>
  </div>
}

export default function PersonalityProfile() {
  const [draft, setDraft] = useState(() => ({ stage: 'questionnaire', likert: {}, text: {}, choices: {}, questionnaire: null, writing: null, sjt: null, ...loadDraft() }))
  useEffect(() => saveDraft(draft), [draft])
  const update = patch => setDraft(prev => ({ ...prev, ...patch }))
  const answer = field => (id, v) => setDraft(prev => ({ ...prev, [field]: { ...prev[field], [id]: v } }))

  const { questionnaire, writing, sjt } = draft
  const sources = [questionnaire, sjt, writing].filter(Boolean).length

  return <div className="page accent-personality">
    <div className="page-heading">
      <div><p className="eyebrow">COMPONENT 02 / CAREER INTELLIGENCE</p><h1>Discover your work personality</h1><p className="page-description">Understand your personality traits, behavioural patterns and decision-making style to find careers that fit you.</p></div>
      <span className="component-icon"><Icon name="personality" size={28} /></span>
    </div>

    <nav className="card personality-stages" aria-label="Assessment stages" id="personality-stage">
      {STAGES.map((stage, i) => {
        const isFinal = stage.id === 'final'
        const locked = isFinal && !sources
        const done = !isFinal && draft[stage.id]
        return <button key={stage.id} type="button" disabled={!stage.ready || locked} aria-current={draft.stage === stage.id ? 'step' : undefined}
          className={draft.stage === stage.id ? 'is-active' : ''} onClick={() => update({ stage: stage.id })}>
          <span className="step-number">0{i + 1}</span>
          <span><strong>{stage.name}</strong><small>{stage.detail}</small></span>
          <span className={`status ${done || (isFinal && !locked) ? 'status-ai' : 'status-neutral'}`}>
            {!stage.ready ? 'Coming soon' : isFinal ? (locked ? 'Locked' : 'View') : done ? <><Icon name="check" size={13} /> Done</> : 'To do'}
          </span>
        </button>
      })}
    </nav>

    {/* The profile comes first in the DOM so it sits above the form on one-column layouts;
        on wide screens CSS places it in the right column. */}
    {draft.stage === 'final' && sources ? <FinalProfile draft={draft} /> : <div className="personality-layout">
      <section className="card personality-results" aria-live="polite">
        <h2>Your profile so far</h2>
        {!sources ? <div className="personality-empty">
          <span className="component-icon"><Icon name="pulse" size={24} /></span>
          <p className="muted">Complete any of the three parts to see your Big Five profile here.</p>
        </div> : <>
          <div className="personality-legend">
            {questionnaire && <span><i className="personality-key-questionnaire" />Your answers · questionnaire</span>}
            {sjt && <span><i className="personality-key-sjt" />Your choices · scenarios · <span className="personality-badge">Draft scoring key</span></span>}
            {writing && <span><i className="personality-key-writing" />Your writing · <span className="personality-badge">Text-only · low reliability</span></span>}
          </div>
          {questionnaire?.warnings?.map(w => <p key={w} className="personality-warning" role="alert">{w}</p>)}
          {TRAITS.map(trait => <TraitRow key={trait.code} trait={trait} level={questionnaire?.traits[trait.code]} choices={sjt?.traits[trait.code]} writing={writing?.traits[trait.code]} />)}
          <p className="personality-note"><Icon name="check" size={15} />
            {sources === 3
              ? 'All three parts are complete. Open 04 Your profile for your combined result and consistency score.'
              : `${sources} of 3 parts complete. Finish the others so your answers, choices and writing can be compared.`}
          </p>
          {sources === 3 && <button type="button" className="button-ai personality-see-profile" onClick={() => update({ stage: 'final' })}>See my combined profile <Icon name="arrow" size={16} /></button>}
        </>}
      </section>

      {draft.stage === 'writing'
        ? <Writing answers={draft.text} onAnswer={answer('text')} onScored={r => update({ writing: r })} />
        : draft.stage === 'sjt'
          ? <Scenarios answers={draft.choices} onAnswer={answer('choices')} onScored={r => update({ sjt: r })} />
          : <Questionnaire answers={draft.likert} onAnswer={answer('likert')} onScored={r => update({ questionnaire: r })} />}
    </div>}
  </div>
}
