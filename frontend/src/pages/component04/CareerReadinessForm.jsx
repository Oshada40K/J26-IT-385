// Owner: Dewmi - Component 04: Career Readiness Assessment form.
// Collects skill confidence, learning preferences and practical experience for the career
// selected from the Component 03 recommendations. Roadmap generation is not part of this form.
import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import Icon from '../../components/Icon.jsx'
import { ErrorState, PageLoader, SkeletonForm, Spinner } from '../../components/loading/index.js'
import { getCareers, getQuestions, loadCareerMatches, loadCvSkills, submitAssessment } from './assessmentApi.js'
import { cached, candidateKey, hasCached, invalidate, peek } from '../../api/resourceCache.js'
import './CareerReadinessForm.css'

const CONFIDENCE_PROMPT = 'Rate how confident you are that you can use this skill to complete a practical task.'
const RATINGS = [
  { value: 'not_studied', label: 'Not studied' },
  { value: 1, label: 'Not confident' },
  { value: 2, label: 'Slightly confident' },
  { value: 3, label: 'Moderately confident' },
  { value: 4, label: 'Confident' },
  { value: 5, label: 'Very confident' },
]
const METHODS = [
  { value: 'online_courses', label: 'Online courses' },
  { value: 'video_tutorials', label: 'Video tutorials' },
  { value: 'reading', label: 'Reading documentation and books' },
  { value: 'hands_on_projects', label: 'Hands-on projects' },
  { value: 'interactive_exercises', label: 'Interactive coding exercises' },
  { value: 'instructor_led', label: 'Instructor-led classes' },
  { value: 'group_learning', label: 'Group learning' },
  { value: 'other', label: 'Other' },
]
const HOURS = [
  { value: '1-3', label: '1–3 hours' },
  { value: '4-6', label: '4–6 hours' },
  { value: '7-10', label: '7–10 hours' },
  { value: '11-15', label: '11–15 hours' },
  { value: '15+', label: 'More than 15 hours' },
]
const EXPERIENCE = [
  { key: 'num_projects', label: 'How many relevant projects have you completed?' },
  { key: 'num_certifications', label: 'How many relevant professional certifications have you obtained?' },
  { key: 'num_internships', label: 'How many relevant internships have you completed?' },
]
const MAX_COUNT = 1000
const emptyExperience = { num_projects: '', num_certifications: '', num_internships: '' }
const norm = value => String(value || '').trim().toLowerCase().replace(/\s+/g, ' ')

function experienceError(value) {
  if (String(value).trim() === '') return 'Enter a number. Use 0 if you have none.'
  if (!/^\d+$/.test(String(value).trim())) return 'Enter a whole number of 0 or more.'
  if (Number(value) > MAX_COUNT) return `Enter a number of ${MAX_COUNT} or less.`
  return ''
}

// Errors in form order, so the first key is the first field to fix.
function validate(skills, form) {
  const errors = {}
  for (const skill of skills) {
    if (form.ratings[skill.skill_id] === undefined) errors[`skill-${skill.skill_id}`] = 'Select a confidence level, or choose "Not studied".'
  }
  if (!form.methods.length) errors.methods = 'Select at least one learning method.'
  else if (form.methods.includes('other') && !form.otherText.trim()) errors.other = 'Describe your other learning method.'
  if (!form.hours) errors.hours = 'Select how many hours per week you can dedicate to learning.'
  for (const { key } of EXPERIENCE) {
    const message = experienceError(form.experience[key])
    if (message) errors[`exp-${key}`] = message
  }
  return errors
}

const fieldId = key => key.startsWith('skill-') ? `c4-${key}-0` : key === 'methods' ? 'c4-method-online_courses' : key === 'hours' ? 'c4-hours-1-3' : `c4-${key}`

function FieldError({ id, message }) {
  return message ? <p className="c4-field-error" id={id} role="alert">{message}</p> : null
}

function CareerPicker({ careers, matches, careerId, onChange, cvSkillCount }) {
  return <section className="card c4-career" aria-labelledby="c4-career-title">
    <div className="c4-section-heading">
      <span className="component-icon"><Icon name="career" size={22} /></span>
      <div><h2 id="c4-career-title">Selected career</h2><p className="muted">The assessment is tailored to the career you want to work towards.</p></div>
    </div>
    {matches.length > 0 && <>
      <p className="c4-label">Your Component 03 career matches</p>
      <div className="c4-match-list" role="radiogroup" aria-label="Component 03 career matches">
        {matches.map(match => {
          const supported = Boolean(match.careerId)
          const selected = supported && match.careerId === careerId
          return <label key={match.ranking} className={`c4-match ${selected ? 'is-selected' : ''} ${supported ? '' : 'is-disabled'}`}>
            <input type="radio" name="c4-career-match" disabled={!supported} checked={selected} onChange={() => onChange(match.careerId)} />
            <span className="rank-badge">{match.ranking}</span>
            <span className="c4-match-text"><strong>{match.job}</strong><small>{supported ? `Match score ${Number(match.score).toFixed(1)}` : 'Not covered by Component 04'}</small></span>
            {selected && <Icon name="check" size={17} />}
          </label>
        })}
      </div>
    </>}
    <label className="c4-label" htmlFor="c4-career-select">{matches.length ? 'Or choose another IT career' : 'Choose your target career'}</label>
    <select id="c4-career-select" value={careerId} onChange={event => onChange(event.target.value)}>
      <option value="" disabled>Select a career</option>
      {careers.map(career => <option key={career.career_id} value={career.career_id}>{career.career_name}</option>)}
    </select>
    <p className="c4-source-note">
      <Icon name="spark" size={15} />
      {cvSkillCount
        ? `Skills are selected from the O*NET requirements for this career and the ${cvSkillCount} skills found in your CV.`
        : <>Skills are selected from the O*NET requirements for this career. <Link to="/">Upload your CV</Link> to include your own skills.</>}
    </p>
  </section>
}

function ProgressCard({ sections, percent }) {
  return <nav className="card c4-progress" aria-label="Assessment progress">
    <div className="c4-progress-top"><strong>Assessment progress</strong><span>{percent}% complete</span></div>
    <div className="c4-progress-bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} aria-label="Assessment completion"><span style={{ width: `${percent}%` }} /></div>
    <ol className="c4-steps">
      {sections.map((section, index) => {
        const done = section.done === section.total
        return <li key={section.id}><a href={`#${section.id}`} className={done ? 'is-done' : ''}>
          <span className="c4-step-number">{done ? <Icon name="check" size={14} /> : index + 1}</span>
          <span><strong>{section.title}</strong><small>{section.done} of {section.total} answered</small></span>
        </a></li>
      })}
    </ol>
  </nav>
}

function SkillQuestion({ skill, index, value, error, onChange }) {
  const errorId = `c4-skill-${skill.skill_id}-error`
  return <fieldset className={`c4-skill ${error ? 'has-error' : ''}`} aria-describedby={`c4-confidence-prompt${error ? ` ${errorId}` : ''}`}>
    <legend>
      <span className="c4-skill-number">{String(index + 1).padStart(2, '0')}</span>
      <span className="c4-skill-name">{skill.skill_name}</span>
      <span className="c4-tags">
        {skill.in_cv && <span className="c4-tag c4-tag-cv">In your CV</span>}
        <span className="c4-tag">{skill.skill_level}</span>
      </span>
    </legend>
    <div className="c4-rating-options">
      {RATINGS.map((rating, i) => <label key={rating.value} className={`${value === rating.value ? 'is-selected' : ''} ${rating.value === 'not_studied' ? 'c4-not-studied' : ''}`}>
        <input type="radio" id={`c4-skill-${skill.skill_id}-${i}`} name={`c4-skill-${skill.skill_id}`} checked={value === rating.value} onChange={() => onChange(rating.value)} />
        {rating.value === 'not_studied' ? <span>Not studied</span> : <><b>{rating.value}</b><span>{rating.label}</span></>}
      </label>)}
    </div>
    <FieldError id={errorId} message={error} />
  </fieldset>
}

// Answers from a previously stored assessment, so students can update rather than start again.
function previousAnswers(record) {
  const form = record?.form || {}
  const prefs = form.preferences || {}
  const activity = form.activity || {}
  return {
    careerId: record?.career_id || '',
    ratings: Object.fromEntries((form.confidence || []).map(c => [c.skill_id, c.rating === null ? 'not_studied' : c.rating])),
    methods: prefs.learning_methods || [],
    otherText: prefs.learning_methods_other || '',
    hours: prefs.weekly_hours || '',
    experience: record ? Object.fromEntries(EXPERIENCE.map(({ key }) => [key, String(activity[key] ?? '')])) : emptyExperience,
  }
}

// Career list, C03 matches and C01 skills -> picker data, plus the career to preselect:
// one passed from Component 03 takes priority, then the best supported match.
function deriveBoot({ careers, jobs, cvSkills }, state) {
  const byName = Object.fromEntries(careers.map(c => [norm(c.career_name), c.career_id]))
  const matches = jobs.map(job => ({ ...job, careerId: byName[norm(job.job)] || '' }))
  const passed = state?.careerId || byName[norm(state?.careerName)]
  const preferred = careers.some(c => c.career_id === passed) ? passed : matches.find(m => m.careerId)?.careerId || ''
  return { boot: { loading: false, error: '', careers, matches, cvSkills }, preferred }
}

const questionsKey = (careerId, cvSkills) => `c04:questions:${careerId}:${JSON.stringify(cvSkills)}`

export default function CareerReadinessForm({ initialRecord = null, onSubmitted, onCancel }) {
  const location = useLocation()
  const [initial] = useState(() => previousAnswers(initialRecord))
  // Reopening the form (e.g. "Update my assessment") reuses the data loaded last time, so it
  // renders immediately instead of flashing a loader.
  const bootKey = candidateKey('c04:boot')
  const [cachedBoot] = useState(() => hasCached(bootKey) ? deriveBoot(peek(bootKey), location.state) : null)
  const [boot, setBoot] = useState(() => cachedBoot?.boot ?? { loading: true, error: '', careers: [], matches: [], cvSkills: [] })
  const [reload, setReload] = useState(0)
  const [careerId, setCareerId] = useState(() => initial.careerId || cachedBoot?.preferred || '')
  const [questions, setQuestions] = useState(() => {
    const key = cachedBoot && careerId && questionsKey(careerId, cachedBoot.boot.cvSkills)
    return { loading: false, error: '', data: key && hasCached(key) ? peek(key) : null }
  })
  const [questionsRetry, setQuestionsRetry] = useState(0)
  const [ratings, setRatings] = useState(initial.ratings)
  const [methods, setMethods] = useState(initial.methods)
  const [otherText, setOtherText] = useState(initial.otherText)
  const [hours, setHours] = useState(initial.hours)
  const [experience, setExperience] = useState(initial.experience)
  const [attempted, setAttempted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  useEffect(() => {
    if (cachedBoot && reload === 0) return undefined
    let active = true
    setBoot(prev => ({ ...prev, loading: true, error: '' }))
    cached(bootKey, () => Promise.all([getCareers(), loadCareerMatches(), loadCvSkills()])
      .then(([careers, jobs, cvSkills]) => ({ careers, jobs, cvSkills }))).then(raw => {
      // No C03 matches usually means that service failed; try again next time instead of caching it.
      if (!raw.jobs.length) invalidate(bootKey)
      if (!active) return
      const { boot: next, preferred } = deriveBoot(raw, location.state)
      setBoot(next)
      setCareerId(current => current || preferred)
    }).catch(error => { if (active) setBoot(prev => ({ ...prev, loading: false, error: error.message })) })
    return () => { active = false }
  }, [reload]) // eslint-disable-line react-hooks/exhaustive-deps

  // Wait for the CV skills: asking earlier fetched the questions twice and blanked the form in between.
  useEffect(() => {
    if (!careerId || boot.loading) return undefined
    const key = questionsKey(careerId, boot.cvSkills)
    if (hasCached(key) && questionsRetry === 0) {
      const data = peek(key)
      setQuestions(prev => prev.data === data ? prev : { loading: false, error: '', data })
      return undefined
    }
    let active = true
    setQuestions({ loading: true, error: '', data: null })
    cached(key, () => getQuestions(careerId, boot.cvSkills))
      .then(data => { if (active) setQuestions({ loading: false, error: '', data }) })
      .catch(error => { if (active) setQuestions({ loading: false, error: error.message, data: null }) })
    return () => { active = false }
  }, [careerId, boot.loading, boot.cvSkills, questionsRetry])

  const skills = useMemo(() => questions.data?.skills || [], [questions.data])
  const form = { ratings, methods, otherText, hours, experience }
  const errors = attempted ? validate(skills, form) : {}
  const errorCount = Object.keys(errors).length

  const sections = [
    { id: 'c4-skills', title: 'Skill confidence', total: skills.length, done: skills.filter(s => ratings[s.skill_id] !== undefined).length },
    { id: 'c4-preferences', title: 'Learning preferences', total: 2, done: Number(methods.length > 0 && (!methods.includes('other') || otherText.trim() !== '')) + Number(Boolean(hours)) },
    { id: 'c4-experience', title: 'Practical experience', total: EXPERIENCE.length, done: EXPERIENCE.filter(({ key }) => !experienceError(experience[key])).length },
  ]
  const total = sections.reduce((sum, s) => sum + s.total, 0)
  const percent = total ? Math.round(100 * sections.reduce((sum, s) => sum + s.done, 0) / total) : 0

  function toggleMethod(value) {
    setMethods(current => current.includes(value) ? current.filter(m => m !== value) : [...current, value])
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setAttempted(true)
    setSubmitError('')
    const found = validate(skills, form)
    const first = Object.keys(found)[0]
    if (first) {
      const element = document.getElementById(fieldId(first))
      element?.focus({ preventScroll: true })
      element?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }
    setSubmitting(true)
    try {
      const result = await submitAssessment({
        career_id: careerId,
        confidence: skills.map(s => ({ skill_id: s.skill_id, rating: ratings[s.skill_id] === 'not_studied' ? null : ratings[s.skill_id] })),
        preferences: { learning_methods: methods, learning_methods_other: methods.includes('other') ? otherText.trim() : null, weekly_hours: hours },
        experience: Object.fromEntries(EXPERIENCE.map(({ key }) => [key, Number(experience[key])])),
      })
      onSubmitted?.(result)
    } catch (error) {
      setSubmitError(error.message)
    } finally {
      setSubmitting(false)
    }
  }

  return <>
    {boot.loading ? <PageLoader variant="roadmap" label="Loading your assessment…" skeleton={<SkeletonForm fields={3} />}
      messages={['Preparing Your Readiness Assessment…', 'Loading careers and your CV skills…', 'Matching your top careers…']} />
      : boot.error ? <ErrorState title="We could not prepare your assessment" message={boot.error} onRetry={() => setReload(v => v + 1)} />
      : <>
        <CareerPicker careers={boot.careers} matches={boot.matches} careerId={careerId} cvSkillCount={boot.cvSkills.length}
          onChange={id => { setCareerId(id); setSubmitError('') }} />

        {!careerId ? <div className="card c4-empty"><p>Select a career above to start the assessment.</p></div>
          : questions.loading ? <div className="fx-delayed"><SkeletonForm fields={3} label="Preparing skills for this career…" /></div>
          : questions.error ? <ErrorState title="We could not load the skills for this career" message={questions.error} onRetry={() => setQuestionsRetry(v => v + 1)} />
          : questions.data && <form className="c4-form fx-reveal" onSubmit={handleSubmit} noValidate>
            <ProgressCard sections={sections} percent={percent} />

            {errorCount > 0 && <div className="c4-error-summary" role="alert">
              <strong>Please complete {errorCount} required {errorCount === 1 ? 'field' : 'fields'} before submitting.</strong>
              <span>Fields that need your attention are highlighted below.</span>
            </div>}

            <section className="card c4-section" id="c4-skills" aria-labelledby="c4-skills-title">
              <div className="c4-section-heading">
                <span className="step-number">01</span>
                <div><h2 id="c4-skills-title">Skill Confidence Assessment</h2><p className="muted">{skills.length} key skills for <strong>{questions.data.career_name}</strong></p></div>
              </div>
              <p className="c4-prompt" id="c4-confidence-prompt">{CONFIDENCE_PROMPT}</p>
              {skills.map((skill, index) => <SkillQuestion key={skill.skill_id} skill={skill} index={index} value={ratings[skill.skill_id]}
                error={errors[`skill-${skill.skill_id}`]} onChange={value => setRatings(current => ({ ...current, [skill.skill_id]: value }))} />)}
            </section>

            <section className="card c4-section" id="c4-preferences" aria-labelledby="c4-preferences-title">
              <div className="c4-section-heading">
                <span className="step-number">02</span>
                <div><h2 id="c4-preferences-title">Learning Preferences</h2><p className="muted">Help us understand how and when you learn best.</p></div>
              </div>
              <fieldset className={`c4-question ${errors.methods || errors.other ? 'has-error' : ''}`} aria-describedby={errors.methods ? 'c4-methods-error' : undefined}>
                <legend>1. Which learning methods do you prefer? <small>Select all that apply.</small></legend>
                <div className="c4-choice-grid">
                  {METHODS.map(method => <label key={method.value} className={methods.includes(method.value) ? 'is-selected' : ''}>
                    <input type="checkbox" id={`c4-method-${method.value}`} checked={methods.includes(method.value)} onChange={() => toggleMethod(method.value)} />
                    <span>{method.label}</span>
                  </label>)}
                </div>
                <FieldError id="c4-methods-error" message={errors.methods} />
                {methods.includes('other') && <div className="c4-other">
                  <label htmlFor="c4-other">Please describe your other learning method</label>
                  <input id="c4-other" type="text" maxLength={200} value={otherText} onChange={event => setOtherText(event.target.value)}
                    aria-invalid={Boolean(errors.other)} aria-describedby={errors.other ? 'c4-other-error' : undefined} placeholder="For example, mentoring or podcasts" />
                  <FieldError id="c4-other-error" message={errors.other} />
                </div>}
              </fieldset>
              <fieldset className={`c4-question ${errors.hours ? 'has-error' : ''}`} aria-describedby={errors.hours ? 'c4-hours-error' : undefined}>
                <legend>2. How many hours per week can you dedicate to learning?</legend>
                <div className="c4-choice-grid c4-hours">
                  {HOURS.map(option => <label key={option.value} className={hours === option.value ? 'is-selected' : ''}>
                    <input type="radio" name="c4-hours" id={`c4-hours-${option.value}`} checked={hours === option.value} onChange={() => setHours(option.value)} />
                    <span>{option.label}</span>
                  </label>)}
                </div>
                <FieldError id="c4-hours-error" message={errors.hours} />
              </fieldset>
            </section>

            <section className="card c4-section" id="c4-experience" aria-labelledby="c4-experience-title">
              <div className="c4-section-heading">
                <span className="step-number">03</span>
                <div><h2 id="c4-experience-title">Practical Experience</h2><p className="muted">Count only experience relevant to {questions.data.career_name}. Enter 0 if you have none.</p></div>
              </div>
              <div className="c4-number-grid">
                {EXPERIENCE.map(({ key, label }, index) => {
                  const error = errors[`exp-${key}`]
                  return <div key={key} className={`c4-number ${error ? 'has-error' : ''}`}>
                    <label htmlFor={`c4-exp-${key}`}>{index + 1}. {label}</label>
                    <input id={`c4-exp-${key}`} type="number" min="0" max={MAX_COUNT} step="1" inputMode="numeric" placeholder="0"
                      value={experience[key]} onChange={event => setExperience(current => ({ ...current, [key]: event.target.value }))}
                      onKeyDown={event => { if (['-', '+', 'e', 'E', '.', ','].includes(event.key)) event.preventDefault() }}
                      aria-invalid={Boolean(error)} aria-describedby={error ? `c4-exp-${key}-error` : undefined} />
                    <FieldError id={`c4-exp-${key}-error`} message={error} />
                  </div>
                })}
              </div>
            </section>

            {submitError && <p className="c4-error-summary" role="alert">{submitError}</p>}
            <div className="c4-submit">
              <p className="muted">Your responses are used only for this research assessment.</p>
              <div className="c4-submit-actions">
                {onCancel && <button type="button" className="button-secondary" onClick={onCancel}>Back to my results</button>}
                <button type="submit" className="button-ai" disabled={submitting}>{submitting ? <><Spinner />Analysing…</> : <>Submit Assessment <Icon name="arrow" size={16} /></>}</button>
              </div>
            </div>
          </form>}
      </>}
  </>
}
