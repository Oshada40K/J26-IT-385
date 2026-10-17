import { useState } from 'react'
import Icon from '../../components/Icon.jsx'
import { analyseTextAnswers } from './personalityApi.js'
import './PersonalityProfile.css'

const MIN_WORDS = 20 // the backend rejects shorter text

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
  { name: 'Big Five questionnaire', detail: 'Likert-scale questions on your traits', ready: false },
  { name: 'Behavioural answers', detail: 'Short written answers about how you work', ready: true },
  { name: 'Situational judgement', detail: 'Realistic workplace scenarios', ready: false },
]

const countWords = text => text.trim().split(/\s+/).filter(Boolean).length

function leaning(p) {
  if (Math.abs(p - 0.5) < 0.1) return 'Unclear'
  return p >= 0.5 ? 'Leans high' : 'Leans low'
}

function TraitRow({ trait, p }) {
  const percent = Math.round(p * 100)
  return <div className="personality-trait">
    <div className="personality-trait-heading">
      <div><h3>{trait.name}</h3><small>{p >= 0.5 ? trait.high : trait.low}</small></div>
      <span className="personality-trait-score">{percent}%<small>{leaning(p)}</small></span>
    </div>
    <div className="personality-meter" role="meter" aria-label={`${trait.name}: ${percent}% likely high`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
      <span className="personality-meter-fill" style={{ width: `${percent}%` }} />
      <span className="personality-meter-mid" aria-hidden="true" />
    </div>
  </div>
}

export default function PersonalityProfile() {
  const [answers, setAnswers] = useState(() => Object.fromEntries(QUESTIONS.map(q => [q.id, ''])))
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const totalWords = QUESTIONS.reduce((sum, q) => sum + countWords(answers[q.id]), 0)
  const canSubmit = totalWords >= MIN_WORDS && !loading

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      setResult(await analyseTextAnswers(QUESTIONS.map(q => answers[q.id]).filter(a => a.trim())))
    } catch (err) {
      setResult(null)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return <div className="page accent-personality">
    <div className="page-heading">
      <div><p className="eyebrow">COMPONENT 02 / CAREER INTELLIGENCE</p><h1>Discover your work personality</h1><p className="page-description">Understand your personality traits, behavioural patterns and decision-making style to find careers that fit you.</p></div>
      <span className="component-icon"><Icon name="personality" size={28} /></span>
    </div>

    <section className="card personality-stages" aria-label="Assessment stages">
      {STAGES.map((stage, i) => <div key={stage.name} className={stage.ready ? 'is-ready' : ''}>
        <span className="step-number">0{i + 1}</span>
        <div><strong>{stage.name}</strong><small>{stage.detail}</small></div>
        <span className={`status ${stage.ready ? 'status-ai' : 'status-neutral'}`}>{stage.ready ? 'Available' : 'Coming soon'}</span>
      </div>)}
    </section>

    <div className="personality-layout">
      <form className="card personality-form" onSubmit={submit}>
        <h2>Behavioural answers</h2>
        <p className="muted">Answer in your own words. There are no right or wrong answers. Aim for 80–150 words per question; longer, honest answers give a more reliable estimate.</p>
        {QUESTIONS.map((q, i) => <label key={q.id} className="personality-question">
          <span className="personality-question-label"><span className="step-number">0{i + 1}</span>{q.label}</span>
          <span className="personality-question-prompt">{q.prompt}</span>
          <textarea rows={4} value={answers[q.id]} disabled={loading} onChange={e => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))} />
          <small className="muted">{countWords(answers[q.id])} words</small>
        </label>)}
        <div className="personality-submit">
          <span className={totalWords >= MIN_WORDS ? 'muted' : 'personality-hint'}>{totalWords} words in total{totalWords < MIN_WORDS && ` · at least ${MIN_WORDS} needed`}</span>
          <button type="submit" className="button-ai" disabled={!canSubmit}>{loading ? 'Analysing…' : <>Analyse my answers <Icon name="spark" size={16} /></>}</button>
        </div>
        {loading && <p className="muted" role="status">The first analysis can take up to a minute while the language model loads.</p>}
        {error && <p className="error-message" role="alert">{error}</p>}
      </form>

      <section className="card personality-results" aria-live="polite">
        <h2>Your Big Five estimate</h2>
        {!result ? <div className="personality-empty">
          <span className="component-icon"><Icon name="pulse" size={24} /></span>
          <p className="muted">Your trait estimates will appear here after you analyse your answers.</p>
        </div> : <>
          <p className="muted">Based on {result.word_count} words. Each bar shows how likely the trait is high; the line marks 50%.</p>
          {TRAITS.map(trait => <TraitRow key={trait.code} trait={trait} p={result.traits[trait.code]} />)}
          <p className="personality-note"><Icon name="check" size={15} /> This is a text-only estimate, one of three planned evidence sources. The questionnaire, situational judgement and consistency score will be added next.</p>
        </>}
      </section>
    </div>
  </div>
}
