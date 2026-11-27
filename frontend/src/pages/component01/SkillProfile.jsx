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
  const [domainView, setDomainView] = useState('relevant')
  const [activeCategory, setActiveCategory] = useState('All')
  const [activeSource, setActiveSource] = useState('combined')

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    getSkillDetails().then(data => { if (active) setResult(data) }).catch(err => { if (active) setError(err.message) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [reload])

  const domain = result?.detected_domain
  const primaryDomain = domain?.primary_domain || null
  const primaryOccupation = domain?.primary_occupation || null
  const sourceProfiles = result?.source_profiles || null

  const baseSkills = activeSource === 'combined'
    ? (result?.skills || [])
    : (sourceProfiles?.[activeSource]?.skills || [])

  const relevantSkills = primaryDomain && activeSource === 'combined'
    ? baseSkills.filter(skill => skill.relevant_to_domain ?? (Array.isArray(skill.domains) ? skill.domains.includes(primaryDomain) : true))
    : baseSkills

  const hasOtherSkills = Boolean(primaryDomain && activeSource === 'combined' && relevantSkills.length < baseSkills.length)
  const domainFiltered = (primaryDomain && activeSource === 'combined' && domainView === 'relevant' && relevantSkills.length > 0)
    ? relevantSkills
    : baseSkills

  const categories = ['All', ...Array.from(new Set(domainFiltered.map(s => s.category).filter(Boolean)))]
  const visibleSkills = activeCategory === 'All'
    ? domainFiltered
    : domainFiltered.filter(s => s.category === activeCategory)

  return <div className="page">
    <div className="page-heading"><div><p className="eyebrow">DYNAMIC SKILL INTELLIGENCE</p><h1>Your skill assessment</h1><p className="page-description">Estimated proficiency levels, percentages, and explainable evidence across ESCO, O*NET, and newly discovered skills.</p></div><Link className="button button-secondary" to="/">Upload another CV <Icon name="upload" size={17} /></Link></div>
    {loading ? <div className="card" role="status">Loading your assessment…</div> : error ? <div className="card"><p className="error-message" role="alert">{error}</p><button onClick={() => setReload(value => value + 1)}>Try again</button></div> : !result ? <div className="card skill-empty"><span className="component-icon"><Icon name="document" size={25} /></span><h2>Start with your CV</h2><p>Upload a PDF or DOCX to discover your skills, matched occupations, and explainable evidence.</p><Link className="button" to="/">Choose your CV <Icon name="arrow" size={17} /></Link></div> : <>
      <div className="skill-result-summary card">
        <span className="status status-ai"><Icon name="check" size={15} /> Assessment complete</span>
        <strong>{(result.skills || []).length} skills identified{primaryDomain ? ` · ${relevantSkills.length} aligned with ${primaryDomain}` : ''}</strong>
        <p>{result.limitations}</p>
      </div>

      {domain && <section className="card skill-domain-card" aria-label="Detected candidate domain and occupation">
        <div className="skill-domain-header">
          <div>
            <p className="eyebrow">{domain.is_unknown_occupation ? 'EMERGING / UNKNOWN OCCUPATION PROFILE' : 'DETECTED CAREER FIELD & OCCUPATION'}</p>
            <h2>{primaryOccupation || primaryDomain || 'General / Cross-Disciplinary Profile'}</h2>
            {primaryDomain && primaryOccupation && primaryDomain !== primaryOccupation && <p className="skill-domain-field">Career Field: <strong>{primaryDomain}</strong></p>}
          </div>
          <span className={`skill-domain-confidence confidence-${domain.confidence || 'low'}`}>{domain.confidence || 'low'} confidence</span>
        </div>
        {!!domain.secondary_domains?.length && <p className="skill-domain-secondary">Related fields: {domain.secondary_domains.join(', ')}</p>}
        {!!domain.related_occupations?.length && <div className="skill-occ-matches">
          <span className="skill-occ-label">Matched ESCO / O*NET occupations:</span>
          {domain.related_occupations.slice(0, 4).map(occ => <span className="skill-domain-tag" key={occ.title}>{occ.title} <small>({occ.source?.toUpperCase()})</small></span>)}
        </div>}
        {!!domain.signals?.length && <ul className="skill-domain-signals">{domain.signals.map((signal, index) => <li key={index}>{signal}</li>)}</ul>}
        {hasOtherSkills && <div className="skill-domain-filter" role="group" aria-label="Filter skills by detected domain">
          <button type="button" className={domainView === 'relevant' ? '' : 'button-secondary'} onClick={() => setDomainView('relevant')}>
            {primaryDomain} aligned ({relevantSkills.length})
          </button>
          <button type="button" className={domainView === 'all' ? '' : 'button-secondary'} onClick={() => setDomainView('all')}>
            All extracted skills ({baseSkills.length})
          </button>
        </div>}
      </section>}

      {sourceProfiles && <section className="card skill-sources-card" aria-label="Independent source summaries">
        <div className="skill-source-tabs" role="tablist" aria-label="Assessment source view">
          {[
            { key: 'combined', label: `Combined (${(result.skills || []).length})` },
            { key: 'cv', label: `CV (${sourceProfiles.cv?.skill_count ?? 0})` },
            { key: 'github', label: `GitHub (${sourceProfiles.github?.skill_count ?? 0}) · ${sourceProfiles.github?.status?.replaceAll('_', ' ') || 'not provided'}` },
            { key: 'linkedin', label: `LinkedIn (${sourceProfiles.linkedin?.skill_count ?? 0}) · ${sourceProfiles.linkedin?.status?.replaceAll('_', ' ') || 'not provided'}` },
          ].map(tab => <button key={tab.key} type="button" role="tab" aria-selected={activeSource === tab.key} className={activeSource === tab.key ? '' : 'button-secondary'} onClick={() => { setActiveSource(tab.key); setActiveCategory('All') }}>{tab.label}</button>)}
        </div>
      </section>}

      {categories.length > 2 && <div className="skill-category-bar" role="group" aria-label="Filter by skill category">
        {categories.map(cat => <button key={cat} type="button" className={`skill-cat-pill ${activeCategory === cat ? 'is-active' : ''}`} onClick={() => setActiveCategory(cat)}>{cat}</button>)}
      </div>}

      {['github', 'linkedin'].some(platform => result.external_profiles?.some(profile => profile.platform === platform)) && <div className="skill-profile-detection" aria-label="Detected profiles">
        {['github', 'linkedin'].filter(platform => result.external_profiles.some(profile => profile.platform === platform)).map(platform => <span className={`skill-profile-chip skill-profile-chip-${platform}`} key={platform}><ProfileIcon platform={platform} />{platform === 'github' ? 'GitHub Profile Detected' : 'LinkedIn Profile Detected'}</span>)}
      </div>}

      {visibleSkills.length === 0 && <div className="card"><h2>No skills in this view</h2><p>No skills were extracted for the selected source or category filter. Missing external sources do not reduce your CV assessment.</p></div>}

      <div className="skill-results-grid">{visibleSkills.map(skill => {
        const pct = skill.percentage ?? skill.level * 20
        const xai = skill.xai
        return <article className="card skill-result" key={skill.name}>
          <div className="skill-result-heading">
            <div>
              <h2>{skill.name}</h2>
              <div className="skill-meta-badges">
                {skill.category && <span className="skill-badge-cat">{skill.category}</span>}
                {skill.is_discovered ? <span className="skill-badge-discovered">Newly discovered</span> : skill.taxonomy_source && <span className="skill-badge-source">{skill.taxonomy_source.toUpperCase()}</span>}
              </div>
            </div>
            <span className="skill-level">{pct}% <small>Est. · Lv {skill.level}/5 ({skill.proficiency_label || 'Provisional'})</small></span>
          </div>

          <div className="skill-progress-track" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={`${skill.name} estimated proficiency ${pct}%`}>
            <div className="skill-progress-fill" style={{ width: `${pct}%` }} />
          </div>
          <div className="skill-level-bars" aria-hidden="true">{[1,2,3,4,5].map(level => <span key={level} className={level <= skill.level ? 'filled' : ''} />)}</div>

          <p className="skill-confidence">
            {skill.confidence === 'high' ? 'High evidence confidence' : skill.confidence === 'medium' ? 'Moderate evidence confidence' : 'Limited evidence · review recommended'} · {skill.status.replaceAll('_', ' ')}
          </p>

          {!!skill.occupations?.length && <div className="skill-domain-tags">{skill.occupations.slice(0, 4).map(occ => <span key={occ} className={`skill-domain-tag ${occ === primaryOccupation ? 'is-primary' : ''}`}>{occ}</span>)}</div>}
          <p>{skill.reason}</p>

          {xai && <details className="skill-xai-box">
            <summary>Explainable AI (XAI) breakdown</summary>
            <p className="xai-why"><strong>Why identified:</strong> {xai.why_identified}</p>
            <p className="xai-type"><strong>Evidence basis:</strong> {xai.self_reported_only ? 'Self-reported only' : (xai.evidence_types || []).join(', ').replaceAll('_', ' ')}</p>
            {!!xai.score_factors?.length && <ul className="xai-factors">{xai.score_factors.map((f, idx) => <li key={idx}><strong>{f.factor} (+{f.points}%):</strong> {f.detail}</li>)}</ul>}
            {!!xai.evidence_limitations?.length && <p className="xai-limits"><strong>Limitations:</strong> {xai.evidence_limitations.join(' ')}</p>}
          </details>}

          <details><summary>View supporting evidence ({skill.evidence.length})</summary>{skill.evidence.map((evidence, index) => <blockquote key={index}><small>{evidence.section}{evidence.match_method ? ` · ${evidence.match_method.replaceAll('_', ' ')}` : ''}{typeof evidence.semantic_similarity === 'number' ? ` · sim ${evidence.semantic_similarity.toFixed(2)}` : ''}</small>{evidence.text}</blockquote>)}</details>
        </article>
      })}</div>

      {!!result.external_profiles.length && <section className="card skill-profile-links"><h2>Profiles found in your CV</h2><p>Identifiers only. Ownership and external experience have not been verified.</p>{result.external_profiles.map(profile => <a key={profile.platform} href={profile.url} target="_blank" rel="noopener noreferrer">{profile.platform === 'github' ? 'GitHub' : 'LinkedIn'}: {profile.handle} <Icon name="arrow" size={15} /></a>)}</section>}
      <details className="card skill-method"><summary>Assessment method and limitations</summary><p>{result.assessment_method} · {result.model_version}</p>{result.warnings.map((warning, index) => <p key={index}>{warning}</p>)}</details>
    </>}
  </div>
}
