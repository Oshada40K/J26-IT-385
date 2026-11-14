// Personal and academic details. Inline validation (same rules as the backend), Save / Cancel,
// and the parent warns before leaving with unsaved changes.
import { useEffect, useState } from 'react'
import Icon from '../../components/Icon.jsx'
import { ACADEMIC_YEARS, BIO_LIMIT, INTERESTS, MAX_INTERESTS, REGIONS, WORK_TYPES, formFrom, isDirty, payloadFrom, validate } from './profileModel.js'
import { Field, describedBy } from './profileUi.jsx'

export default function EditDetailsTab({ profile, onSave, onCancel, onDirtyChange }) {
  const [saved, setSaved] = useState(() => formFrom(profile))
  const [form, setForm] = useState(saved)
  const [touched, setTouched] = useState({})
  const [serverErrors, setServerErrors] = useState({})
  const [submitted, setSubmitted] = useState(false)
  const [saving, setSaving] = useState(false)
  const dirty = isDirty(form, saved)
  const errors = { ...validate(form), ...serverErrors }
  const shown = field => (touched[field] || submitted) ? errors[field] : undefined

  useEffect(() => { onDirtyChange(dirty) }, [dirty, onDirtyChange])
  useEffect(() => () => onDirtyChange(false), [onDirtyChange])

  const set = field => event => {
    const value = event.target.value
    setForm(current => ({ ...current, [field]: value }))
    setServerErrors(({ [field]: _, ...rest }) => rest)
  }
  const blur = field => () => setTouched(current => ({ ...current, [field]: true }))
  const pick = (field, value) => setForm(current => ({ ...current, [field]: current[field] === value ? '' : value }))
  const toggleInterest = item => setForm(current => {
    const has = current.interests.includes(item)
    if (!has && current.interests.length >= MAX_INTERESTS) return current
    return { ...current, interests: has ? current.interests.filter(value => value !== item) : [...current.interests, item] }
  })

  async function submit(event) {
    event.preventDefault()
    setSubmitted(true)
    if (Object.keys(validate(form)).length) {
      document.querySelector('.pf-form .has-error input, .pf-form .has-error textarea, .pf-form .has-error select')?.focus()
      return
    }
    setSaving(true)
    try {
      const next = formFrom(await onSave(payloadFrom(form)))
      setSaved(next); setForm(next); setTouched({}); setSubmitted(false)
    } catch (error) {
      if (error.fields) setServerErrors(error.fields)
    } finally { setSaving(false) }
  }

  function cancel() {
    setForm(saved); setTouched({}); setServerErrors({}); setSubmitted(false)
    onCancel()
  }

  const input = (field, label, props = {}) => {
    const id = `pf-${field}`
    return <Field id={id} label={label} hint={props.hint} error={shown(field)} optional={props.optional}>
      <input id={id} name={field} value={form[field]} onChange={set(field)} onBlur={blur(field)} autoComplete={props.autoComplete || 'off'}
        type={props.type || 'text'} inputMode={props.inputMode} placeholder={props.placeholder} required={props.required}
        aria-invalid={Boolean(shown(field))} aria-describedby={describedBy(id, shown(field), props.hint)} />
    </Field>
  }

  return <form className="card pf-card pf-form" onSubmit={submit} noValidate aria-labelledby="pf-edit-title">
    <header className="card-head"><div><h3 id="pf-edit-title">Personal and academic details</h3><p>Only your full name is required.</p></div></header>

    <fieldset><legend>Personal</legend>
      <div className="pf-grid">
        {input('full_name', 'Full name', { autoComplete: 'name', required: true })}
        {input('phone', 'Phone', { optional: true, type: 'tel', autoComplete: 'tel', inputMode: 'tel', placeholder: '+94 77 123 4567' })}
        {input('location', 'Location / country', { optional: true, autoComplete: 'country-name', placeholder: 'Colombo, Sri Lanka' })}
      </div>
    </fieldset>

    <fieldset><legend>Academic</legend>
      <div className="pf-grid">
        {input('university', 'University', { optional: true, autoComplete: 'organization' })}
        {input('degree', 'Degree programme', { optional: true, placeholder: 'BSc (Hons) in Information Technology' })}
        <Field id="pf-academic_year" label="Academic year" optional>
          <select id="pf-academic_year" value={form.academic_year} onChange={set('academic_year')}>
            <option value="">Not set</option>{ACADEMIC_YEARS.map(year => <option key={year}>{year}</option>)}
          </select>
        </Field>
        {input('graduation_year', 'Graduation year', { optional: true, inputMode: 'numeric', placeholder: String(new Date().getFullYear() + 1) })}
      </div>
    </fieldset>

    <fieldset><legend>Links and bio</legend>
      <div className="pf-grid">
        {input('linkedin_url', 'LinkedIn URL', { optional: true, type: 'url', placeholder: 'https://www.linkedin.com/in/your-name' })}
        {input('github_url', 'GitHub URL', { optional: true, type: 'url', placeholder: 'https://github.com/your-username' })}
      </div>
      <Field id="pf-bio" label="Short bio" optional error={shown('bio')}
        counter={<span className={`pf-counter ${form.bio.length > BIO_LIMIT ? 'is-over' : ''}`} aria-live="polite">{form.bio.length}/{BIO_LIMIT}</span>}>
        <textarea id="pf-bio" rows={3} value={form.bio} onChange={set('bio')} onBlur={blur('bio')}
          aria-invalid={Boolean(shown('bio'))} aria-describedby={describedBy('pf-bio', shown('bio'))} />
      </Field>
    </fieldset>

    <fieldset><legend>Career preferences</legend>
      <div className="pf-group" role="group" aria-labelledby="pf-interests-label">
        <p id="pf-interests-label" className="pf-group-label">Career interests <span className="pf-optional">Up to {MAX_INTERESTS}</span></p>
        <div className="chips pf-chips">{INTERESTS.map(item => {
          const on = form.interests.includes(item)
          return <button key={item} type="button" aria-pressed={on} className={on ? 'is-active' : ''} onClick={() => toggleInterest(item)}
            disabled={!on && form.interests.length >= MAX_INTERESTS}>{on && <Icon name="check" size={12} />}{item}</button>
        })}</div>
      </div>
      <Choice label="Preferred work type" options={WORK_TYPES} value={form.work_type} onPick={value => pick('work_type', value)} />
      <Choice label="Preferred region" options={REGIONS} value={form.region} onPick={value => pick('region', value)} />
    </fieldset>

    <div className="pf-form-actions">
      {dirty && <p className="pf-unsaved" role="status"><Icon name="alert" size={14} />You have unsaved changes</p>}
      <button type="button" className="button-secondary" onClick={cancel} disabled={saving}>Cancel</button>
      <button type="submit" disabled={saving || !dirty}>{saving ? 'Saving…' : 'Save changes'}</button>
    </div>
  </form>
}

// Single choice that can be cleared by pressing the selected option again.
function Choice({ label, options, value, onPick }) {
  const id = label.replace(/\W+/g, '-').toLowerCase()
  return <div className="pf-group" role="radiogroup" aria-labelledby={id}>
    <p id={id} className="pf-group-label">{label} <span className="pf-optional">Optional</span></p>
    <div className="chips pf-chips">{options.map(option => <button key={option.value} type="button" role="radio" aria-checked={value === option.value}
      className={value === option.value ? 'is-active' : ''} onClick={() => onPick(option.value)}>{option.label}</button>)}</div>
  </div>
}
