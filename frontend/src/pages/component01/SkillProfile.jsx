import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../../components/Icon.jsx'
import { getSkillDetails } from './skillApi.js'
import './SkillProfile.css'

function ProfileIcon({ platform }) {
  return <svg width="17" height="17" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    {platform === 'github' ? <path d="M12 .9a11.1 11.1 0 0 0-3.51 21.63c.55.1.76-.24.76-.54v-2.07c-3.09.67-3.74-1.31-3.74-1.31-.5-1.28-1.23-1.62-1.23-1.62-1.01-.69.08-.68.08-.68 1.12.08 1.7 1.15 1.7 1.15.99 1.69 2.59 1.2 3.22.92.1-.72.39-1.2.7-1.48-2.47-.28-5.06-1.24-5.06-5.49 0-1.21.43-2.2 1.14-2.97-.11-.28-.49-1.41.11-2.94 0 0 .93-.3 3.05 1.14a10.6 10.6 0 0 1 5.55 0c2.12-1.44 3.05-1.14 3.05-1.14.6 1.53.22 2.66.11 2.94.71.77 1.14 1.76 1.14 2.97 0 4.26-2.6 5.2-5.08 5.48.4.35.75 1.02.75 2.06v3.04c0 .3.2.65.77.54A11.1 11.1 0 0 0 12 .9Z" /> : <>
      <rect x="1" y="1" width="22" height="22" rx="2" />
      <path fill="white" d="M5 9h3v10H5z M6.5 4.7a1.7 1.7 0 1 0 0 3.4 1.7 1.7 0 0 0 0-3.4 M10 9h2.9v1.4c.5-.9 1.4-1.7 3-1.7 3.2 0 3.6 2.1 3.6 4.8V19h-3v-4.9c0-1.2 0-2.7-1.7-2.7s-1.9 1.3-1.9 2.6v5h-3Z" />
    </>}
  </svg>
}

export default function SkillProfile() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)
  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    getSkillDetails().then(data => { if (active) setResult(data) }).catch(err => { if (active) setError(err.message) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [reload])
  return <div className="page">
    <div className="page-heading"><div><p className="eyebrow">YOUR CV, EXPLAINED</p><h1>Your technical strengths</h1><p className="page-description">Estimated skill levels based on the evidence in your CV.</p></div><Link className="button button-secondary" to="/">Upload another CV <Icon name="upload" size={17} /></Link></div>
    {loading ? <div className="card" role="status">Loading your assessment…</div> : error ? <div className="card"><p className="error-message" role="alert">{error}</p><button onClick={() => setReload(value => value + 1)}>Try again</button></div> : !result ? <div className="card skill-empty"><span className="component-icon"><Icon name="document" size={25} /></span><h2>Start with your CV</h2><p>Upload a PDF or DOCX to discover your skills and the evidence behind each estimate.</p><Link className="button" to="/">Choose your CV <Icon name="arrow" size={17} /></Link></div> : <>
      <div className="skill-result-summary card"><span className="status status-ai"><Icon name="check" size={15} /> Assessment complete</span><strong>{result.skills.length} technical skills identified</strong><p>{result.limitations}</p></div>
      {['github', 'linkedin'].some(platform => result.external_profiles?.some(profile => profile.platform === platform)) && <div className="skill-profile-detection" aria-label="Detected profiles">
        {['github', 'linkedin'].filter(platform => result.external_profiles.some(profile => profile.platform === platform)).map(platform => <span className={`skill-profile-chip skill-profile-chip-${platform}`} key={platform}><ProfileIcon platform={platform} />{platform === 'github' ? 'GitHub Profile Detected' : 'LinkedIn Profile Detected'}</span>)}
      </div>}
      {result.skills.length === 0 && <div className="card"><h2>No recognized technical skills found</h2><p>Your CV was processed successfully. Add specific technologies and examples of your work, then upload an updated CV.</p></div>}
      <div className="skill-results-grid">{result.skills.map(skill => <article className="card skill-result" key={skill.name}><div className="skill-result-heading"><h2>{skill.name}</h2><span className="skill-level">{skill.level}<small>/ 5 estimated</small></span></div><div className="skill-level-bars" aria-hidden="true">{[1,2,3,4,5].map(level => <span key={level} className={level <= skill.level ? 'filled' : ''} />)}</div><p className="skill-confidence">{skill.confidence === 'low' ? 'Limited evidence · review recommended' : 'Moderate evidence'} · {skill.status.replaceAll('_', ' ')}</p><p>{skill.reason}</p><details><summary>View CV evidence ({skill.evidence.length})</summary>{skill.evidence.map((evidence, index) => <blockquote key={index}><small>{evidence.section}</small>{evidence.text}</blockquote>)}</details></article>)}</div>
      {!!result.external_profiles.length && <section className="card skill-profile-links"><h2>Profiles found in your CV</h2><p>Identifiers only. Ownership and external experience have not been verified.</p>{result.external_profiles.map(profile => <a key={profile.platform} href={profile.url} target="_blank" rel="noopener noreferrer">{profile.platform === 'github' ? 'GitHub' : 'LinkedIn'}: {profile.handle} <Icon name="arrow" size={15} /></a>)}</section>}
      <details className="card skill-method"><summary>Assessment method and limitations</summary><p>{result.assessment_method} · {result.model_version}</p>{result.warnings.map((warning, index) => <p key={index}>{warning}</p>)}</details>
    </>}
  </div>
}
