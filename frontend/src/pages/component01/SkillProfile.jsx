import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../../components/Icon.jsx'
import { getSkillDetails } from './skillApi.js'

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
      {result.skills.length === 0 && <div className="card"><h2>No recognized technical skills found</h2><p>Your CV was processed successfully. Add specific technologies and examples of your work, then upload an updated CV.</p></div>}
      <div className="skill-results-grid">{result.skills.map(skill => <article className="card skill-result" key={skill.name}><div className="skill-result-heading"><h2>{skill.name}</h2><span className="skill-level">{skill.level}<small>/ 5 estimated</small></span></div><div className="skill-level-bars" aria-hidden="true">{[1,2,3,4,5].map(level => <span key={level} className={level <= skill.level ? 'filled' : ''} />)}</div><p className="skill-confidence">{skill.confidence === 'low' ? 'Limited evidence · review recommended' : 'Moderate evidence'} · {skill.status.replaceAll('_', ' ')}</p><p>{skill.reason}</p><details><summary>View CV evidence ({skill.evidence.length})</summary>{skill.evidence.map((evidence, index) => <blockquote key={index}><small>{evidence.section}</small>{evidence.text}</blockquote>)}</details></article>)}</div>
      {!!result.external_profiles.length && <section className="card skill-profile-links"><h2>Profiles found in your CV</h2><p>Identifiers only. Ownership and external experience have not been verified.</p>{result.external_profiles.map(profile => <a key={profile.platform} href={profile.url} target="_blank" rel="noopener noreferrer">{profile.platform === 'github' ? 'GitHub' : 'LinkedIn'}: {profile.handle} <Icon name="arrow" size={15} /></a>)}</section>}
      <details className="card skill-method"><summary>Assessment method and limitations</summary><p>{result.assessment_method} · {result.model_version}</p>{result.warnings.map((warning, index) => <p key={index}>{warning}</p>)}</details>
    </>}
  </div>
}
