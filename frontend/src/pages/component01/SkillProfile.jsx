import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../../components/Icon.jsx'
import { getSkillDetails, uploadCV } from './skillApi.js'
import './SkillProfile.css'

function ProfileIcon({ platform }) {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    {platform === 'github' ? <path d="M12 .9a11.1 11.1 0 0 0-3.51 21.63c.55.1.76-.24.76-.54v-2.07c-3.09.67-3.74-1.31-3.74-1.31-.5-1.28-1.23-1.62-1.23-1.62-1.01-.69.08-.68.08-.68 1.12.08 1.7 1.15 1.7 1.15.99 1.69 2.59 1.2 3.22.92.1-.72.39-1.2.7-1.48-2.47-.28-5.06-1.24-5.06-5.49 0-1.21.43-2.2 1.14-2.97-.11-.28-.49-1.41.11-2.94 0 0 .93-.3 3.05 1.14a10.6 10.6 0 0 1 5.55 0c2.12-1.44 3.05-1.14 3.05-1.14.6 1.53.22 2.66.11 2.94.71.77 1.14 1.76 1.14 2.97 0 4.26-2.6 5.2-5.08 5.48.4.35.75 1.02.75 2.06v3.04c0 .3.2.65.77.54A11.1 11.1 0 0 0 12 .9Z" /> : <>
      <rect x="1" y="1" width="22" height="22" rx="2" />
      <path fill="white" d="M5 9h3v10H5z M6.5 4.7a1.7 1.7 0 1 0 0 3.4 1.7 1.7 0 0 0 0-3.4 M10 9h2.9v1.4c.5-.9 1.4-1.7 3-1.7 3.2 0 3.6 2.1 3.6 4.8V19h-3v-4.9c0-1.2 0-2.7-1.7-2.7s-1.9 1.3-1.9 2.6v5h-3Z" />
    </>}
  </svg>
}

function ScoreRing({ value }) {
  const clamped = Math.max(0, Math.min(100, Math.round(value)))
  const radius = 46
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (clamped / 100) * circumference
  return <div className="sp-ring" aria-label={`Overall estimated score ${clamped}%`}>
    <svg width="116" height="116" viewBox="0 0 116 116">
      <defs>
        <linearGradient id="spScoreGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#4338CA" />
          <stop offset="100%" stopColor="#7C3AED" />
        </linearGradient>
      </defs>
      <circle cx="58" cy="58" r={radius} className="sp-ring-bg" />
      <circle
        cx="58"
        cy="58"
        r={radius}
        className="sp-ring-fill"
        stroke="url(#spScoreGrad)"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
      />
    </svg>
    <div className="sp-ring-label">
      <strong>{clamped}%</strong>
      <span>Est. Score</span>
    </div>
  </div>
}

const CLAIM_LABELS = {
  corroborated_practical: 'Corroborated practical evidence',
  corroborated_claimed: 'Corroborated claim (no practical proof yet)',
  cv_practical_only: 'Practical evidence in CV only',
  external_only: 'External profile only',
  claimed_only: 'Claimed without practical evidence',
}

export default function SkillProfile() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)
  const [domainView, setDomainView] = useState('relevant')
  const [activeCategory, setActiveCategory] = useState('All')
  const [activeSource, setActiveSource] = useState('combined')
  const [compareFilter, setCompareFilter] = useState('all')

  const [showMultiUpload, setShowMultiUpload] = useState(false)
  const [cvFile, setCvFile] = useState(null)
  const [githubUrl, setGithubUrl] = useState('')
  const [linkedinUrl, setLinkedinUrl] = useState('')
  const [linkedinText, setLinkedinText] = useState('')
  const [consentGithub, setConsentGithub] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [uploadError, setUploadError] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    getSkillDetails().then(data => { if (active) setResult(data) }).catch(err => { if (active) setError(err.message) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [reload])

  async function handleMultiSourceSubmit(event) {
    event.preventDefault()
    if (!cvFile || submitting) return
    setSubmitting(true)
    setUploadError('')
    try {
      await uploadCV(cvFile, {
        githubUsername: githubUrl.trim() || undefined,
        linkedinUsername: linkedinUrl.trim() || undefined,
        analyzeGithub: consentGithub,
        linkedinText: linkedinText.trim() || undefined,
      })
      setShowMultiUpload(false)
      setReload(v => v + 1)
    } catch (err) {
      setUploadError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const domain = result?.detected_domain
  const primaryDomain = domain?.primary_domain || null
  const primaryOccupation = domain?.primary_occupation || null
  const sourceProfiles = result?.source_profiles || null
  const comparison = result?.cross_source_comparison || null
  const allCombinedSkills = result?.skills || []

  // Executive dashboard metrics derived directly from stored assessment skills.
  const skillPct = s => s.percentage ?? s.level * 20
  const overallScore = allCombinedSkills.length
    ? Math.round(allCombinedSkills.reduce((sum, s) => sum + skillPct(s), 0) / allCombinedSkills.length)
    : 0
  const avgLevel = allCombinedSkills.length
    ? (allCombinedSkills.reduce((sum, s) => sum + (s.level || 0), 0) / allCombinedSkills.length).toFixed(1)
    : '0.0'
  const practicalCount = allCombinedSkills.filter(s => s.evidence_tier === 'practical_implementation' || (s.xai && !s.xai.self_reported_only && s.level >= 3)).length
  const highOrMedCount = allCombinedSkills.filter(s => s.confidence === 'high' || s.confidence === 'medium').length

  // Mutual exclusion: Best-Performing Skills = practical/strong skills (level >= 3); never overlap with Improvement Areas.
  const practicalStrong = [...allCombinedSkills]
    .filter(s => s.level >= 3 || s.evidence_tier === 'practical_implementation')
    .sort((a, b) => skillPct(b) - skillPct(a) || b.level - a.level || a.name.localeCompare(b.name))
  const bestSkills = (practicalStrong.length ? practicalStrong : [...allCombinedSkills]
    .filter(s => skillPct(s) >= 40)
    .sort((a, b) => skillPct(b) - skillPct(a) || a.name.localeCompare(b.name)))
    .slice(0, 5)
  const bestNames = new Set(bestSkills.map(s => s.name))

  const improvementSkills = [...allCombinedSkills]
    .filter(s => !bestNames.has(s.name) && (s.level <= 2 || s.confidence === 'low' || s.evidence_tier !== 'practical_implementation'))
    .sort((a, b) => skillPct(a) - skillPct(b) || a.level - b.level || a.name.localeCompare(b.name))
    .slice(0, 5)

  const recommendations = result?.recommendations || null
  const recBySkill = Object.fromEntries((recommendations?.evidence_gaps || []).map(r => [r.skill, r.recommendation]))

  // Category chart data
  const categoryMap = {}
  allCombinedSkills.forEach(s => {
    const cat = s.category || 'Domain-specific skills'
    if (!categoryMap[cat]) categoryMap[cat] = { name: cat, count: 0, totalPct: 0 }
    categoryMap[cat].count += 1
    categoryMap[cat].totalPct += skillPct(s)
  })
  const categoryStats = Object.values(categoryMap)
    .map(c => ({ ...c, avgPct: Math.round(c.totalPct / c.count) }))
    .sort((a, b) => b.count - a.count || b.avgPct - a.avgPct)

  const topCategories = [...categoryStats].sort((a, b) => b.avgPct - a.avgPct).slice(0, 3)

  // Level distribution (1..5)
  const levelCounts = [5, 4, 3, 2, 1].map(lv => ({
    level: lv,
    label: { 5: 'Expert', 4: 'Advanced', 3: 'Intermediate', 2: 'Basic', 1: 'Familiarity' }[lv],
    count: allCombinedSkills.filter(s => s.level === lv).length,
  }))

  // Filtered inventory view
  const baseSkills = activeSource === 'combined'
    ? allCombinedSkills
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

  const comparedSkills = (comparison?.skills || []).filter(item => {
    if (compareFilter === 'multi') return item.multi_source
    if (compareFilter === 'single') return item.single_source
    if (compareFilter === 'gaps') return item.claim_vs_practice_status === 'claimed_only' || item.claim_vs_practice_status === 'corroborated_claimed'
    return true
  })

  return <div className="page sp-dashboard">
    <header className="page-heading">
      <div>
        <p className="eyebrow">COMPONENT 01 · SKILL ASSESSMENT DASHBOARD</p>
        <h1>Skill Intelligence Overview</h1>
        <p className="page-description">Estimated proficiency scores, key strengths, and improvement areas derived from your CV and linked profiles.</p>
      </div>
      <div className="skill-header-actions">
        <button type="button" className="button button-secondary" onClick={() => setShowMultiUpload(v => !v)}>
          {showMultiUpload ? 'Close multi-source form' : 'Multi-source input'}
        </button>
        <Link className="button" to="/">Upload another CV <Icon name="upload" size={17} /></Link>
      </div>
    </header>

    {showMultiUpload && <form className="card skill-multi-upload" onSubmit={handleMultiSourceSubmit}>
      <h2>Multi-source assessment (CV + GitHub + LinkedIn)</h2>
      <p className="skill-multi-note">Only permitted public GitHub API data and candidate-provided LinkedIn text are analyzed. Missing sources never penalize your CV assessment.</p>
      <div className="skill-multi-grid">
        <label>
          <span>CV / Resume (PDF or DOCX) *</span>
          <input type="file" accept=".pdf,.docx" required onChange={e => setCvFile(e.target.files?.[0] || null)} />
        </label>
        <label>
          <span>GitHub Profile URL or Username (optional)</span>
          <input type="text" placeholder="e.g. https://github.com/username" value={githubUrl} onChange={e => setGithubUrl(e.target.value)} />
        </label>
        <label>
          <span>LinkedIn Profile URL (optional)</span>
          <input type="text" placeholder="e.g. https://www.linkedin.com/in/username" value={linkedinUrl} onChange={e => setLinkedinUrl(e.target.value)} />
        </label>
        <label className="skill-checkbox-row">
          <input type="checkbox" checked={consentGithub} onChange={e => setConsentGithub(e.target.checked)} />
          <span>Authorize public GitHub repository & commit sampling</span>
        </label>
      </div>
      <label className="skill-linkedin-text">
        <span>Authorized LinkedIn Profile / Skills Export Text (optional)</span>
        <textarea rows={3} placeholder="Paste your exported LinkedIn summary, skills, or experience text here..." value={linkedinText} onChange={e => setLinkedinText(e.target.value)} />
      </label>
      {uploadError && <p className="error-message" role="alert">{uploadError}</p>}
      <div className="skill-multi-actions">
        <button type="submit" disabled={!cvFile || submitting}>{submitting ? 'Analyzing sources…' : 'Run Multi-Source Assessment'}</button>
      </div>
    </form>}

    {loading ? <div className="card sp-state" role="status">Loading your assessment…</div> : error ? <div className="card sp-state"><p className="error-message" role="alert">{error}</p><button onClick={() => setReload(value => value + 1)}>Try again</button></div> : !result ? <div className="card skill-empty"><span className="component-icon"><Icon name="document" size={25} /></span><h2>Start with your CV</h2><p>Upload a PDF or DOCX to view your overall score, top strengths, and skill evidence.</p><div className="skill-empty-actions"><Link className="button" to="/">Choose your CV <Icon name="arrow" size={17} /></Link><button type="button" className="button button-secondary" onClick={() => setShowMultiUpload(true)}>Submit CV + GitHub / LinkedIn</button></div></div> : <>

      {/* 1. HERO KPI & TOP STRENGTHS SUMMARY */}
      <section className="sp-hero-grid" aria-label="Overall score and top strengths">
        <article className="card sp-score-hero">
          <ScoreRing value={overallScore} />
          <div className="sp-score-meta">
            <span className="status status-ai"><Icon name="check" size={14} /> Assessment Complete</span>
            <h2>{allCombinedSkills.length} Skills Assessed</h2>
            <div className="sp-kpi-row">
              <div><small>Avg. Level</small><strong>{avgLevel} / 5</strong></div>
              <div><small>Practical Evidence</small><strong>{practicalCount} / {allCombinedSkills.length}</strong></div>
              <div><small>Med/High Confidence</small><strong>{highOrMedCount}</strong></div>
            </div>
            <p className="sp-disclaimer">{result.limitations}</p>
          </div>
        </article>

        <article className="card sp-strengths-hero">
          <div className="sp-card-head">
            <div>
              <p className="eyebrow">{domain?.is_unknown_occupation ? 'EMERGING / UNMAPPED PROFILE' : 'DETECTED PROFILE & TOP STRENGTHS'}</p>
              <h2>{primaryOccupation || primaryDomain || 'Cross-Disciplinary Profile'}</h2>
              {(primaryDomain || domain?.career_stage?.label) && <p className="sp-subline">
                {primaryDomain && primaryDomain !== primaryOccupation ? <>Field: <strong>{primaryDomain}</strong></> : null}
                {domain?.career_stage?.label ? <> · Stage: <strong>{domain.career_stage.label}</strong></> : null}
              </p>}
            </div>
            {domain && <span className={`skill-domain-confidence confidence-${domain.confidence || 'low'}`}>{domain.confidence || 'low'} confidence</span>}
          </div>

          {!!topCategories.length && <div className="sp-top-cats">
            <span className="sp-label">Strongest areas:</span>
            {topCategories.map(cat => <span key={cat.name} className="sp-strength-pill">{cat.name} · {cat.avgPct}%</span>)}
          </div>}

          {!!domain?.related_occupations?.length && <div className="sp-occ-row">
            <span className="sp-label">Aligned occupations:</span>
            {domain.related_occupations.slice(0, 3).map(occ => <span className="skill-domain-tag" key={occ.title}>{occ.title}</span>)}
          </div>}

          {['github', 'linkedin'].some(p => result.external_profiles?.some(pr => pr.platform === p)) && <div className="sp-ext-chips">
            {['github', 'linkedin'].filter(p => result.external_profiles.some(pr => pr.platform === p)).map(p => <span className={`skill-profile-chip skill-profile-chip-${p}`} key={p}><ProfileIcon platform={p} />{p === 'github' ? 'GitHub Linked' : 'LinkedIn Linked'}</span>)}
          </div>}
        </article>
      </section>

      {/* 2. BEST-PERFORMING SKILLS & KEY IMPROVEMENT AREAS */}
      {allCombinedSkills.length > 0 && <section className="sp-two-col" aria-label="Best-performing skills and improvement areas">
        <article className="card sp-highlight-card">
          <div className="sp-section-title">
            <h3>Best-Performing Skills</h3>
            <span className="sp-pill sp-pill-good">Top {bestSkills.length}</span>
          </div>
          <p className="sp-muted">Highest estimated proficiency backed by available evidence.</p>
          {bestSkills.length === 0 ? <p className="sp-empty-note">No practical or corroborated skills above baseline yet.</p> : <div className="sp-rank-list">
            {bestSkills.map(skill => {
              const pct = skillPct(skill)
              return <div className="sp-rank-item" key={skill.name}>
                <div className="sp-rank-top">
                  <strong>{skill.name}</strong>
                  <span className="sp-rank-score">{pct}% <small>Lv {skill.level}</small></span>
                </div>
                <div className="sp-bar-track"><div className="sp-bar-fill sp-bar-good" style={{ width: `${pct}%` }} /></div>
                <div className="sp-rank-foot">
                  <span>{skill.category}</span>
                  <span>{skill.xai?.primary_evidence_label || (skill.xai?.self_reported_only ? 'Self-reported' : 'Practical evidence')}</span>
                </div>
              </div>
            })}
          </div>}
        </article>

        <article className="card sp-highlight-card">
          <div className="sp-section-title">
            <h3>Key Improvement Areas</h3>
            <span className="sp-pill sp-pill-warn">{improvementSkills.length ? `${improvementSkills.length} to strengthen` : 'Strong coverage'}</span>
          </div>
          <p className="sp-muted">Skills with self-reported, training, or observational evidence needing practical proof.</p>
          {improvementSkills.length === 0 ? <p className="sp-empty-note">All assessed skills currently show practical implementation evidence.</p> : <div className="sp-rank-list">
            {improvementSkills.map(skill => {
              const pct = skillPct(skill)
              const tip = recBySkill[skill.name] || (skill.xai?.self_reported_only
                ? 'Listed in skills without project/work implementation evidence yet.'
                : 'Add concrete practical examples to verify independent proficiency.')
              return <div className="sp-rank-item" key={skill.name}>
                <div className="sp-rank-top">
                  <strong>{skill.name}</strong>
                  <span className="sp-rank-score sp-score-warn">{pct}% <small>Lv {skill.level}</small></span>
                </div>
                <div className="sp-bar-track"><div className="sp-bar-fill sp-bar-warn" style={{ width: `${pct}%` }} /></div>
                <p className="sp-improve-tip">{tip}</p>
              </div>
            })}
          </div>}
          {!!recommendations?.missing_occupation_skills?.length && <div className="sp-gap-box">
            <span className="sp-label">Role-relevant skills not yet evidenced:</span>
            <div className="skill-domain-tags">{recommendations.missing_occupation_skills.slice(0, 4).map(g => <span className="skill-domain-tag" key={g.skill}>{g.skill}</span>)}</div>
          </div>}
        </article>
      </section>}

      {/* 3. SIMPLE VISUAL CHARTS */}
      {allCombinedSkills.length > 0 && <section className="sp-two-col" aria-label="Skill analytics charts">
        <article className="card sp-chart-card">
          <h3>Skills by Category</h3>
          <p className="sp-muted">Average estimated proficiency and skill count per category.</p>
          <div className="sp-chart-bars">
            {categoryStats.map(cat => <div className="sp-chart-row" key={cat.name}>
              <div className="sp-chart-label"><span>{cat.name}</span><small>{cat.count} skill{cat.count === 1 ? '' : 's'} · {cat.avgPct}%</small></div>
              <div className="sp-bar-track"><div className="sp-bar-fill" style={{ width: `${cat.avgPct}%` }} /></div>
            </div>)}
          </div>
        </article>

        <article className="card sp-chart-card">
          <h3>Proficiency Level Distribution</h3>
          <p className="sp-muted">Breakdown across the five-level provisional rubric (1–5).</p>
          <div className="sp-chart-bars">
            {levelCounts.map(item => {
              const share = allCombinedSkills.length ? Math.round((item.count / allCombinedSkills.length) * 100) : 0
              return <div className="sp-chart-row" key={item.level}>
                <div className="sp-chart-label"><span>Level {item.level} · {item.label}</span><small>{item.count} ({share}%)</small></div>
                <div className="sp-bar-track"><div className="sp-bar-fill sp-bar-ai" style={{ width: `${share}%` }} /></div>
              </div>
            })}
          </div>
        </article>
      </section>}

      {/* 4. COLLAPSIBLE "EXPLORE MORE..." DETAILED ANALYSIS & FULL SKILL INVENTORY */}
      <details className="card sp-explore-more">
        <summary className="sp-explore-summary">
          <div>
            <strong>Explore more…</strong>
            <small>View all {allCombinedSkills.length} assessed skills, source filters, XAI evidence & cross-source comparison</small>
          </div>
          <span className="sp-explore-cta">Show detailed analysis</span>
        </summary>

        <div className="sp-explore-body">
          {sourceProfiles && <section className="skill-source-summaries" aria-label="Independent source profiles">
            {[
              { key: 'cv', title: 'CV / Resume', data: sourceProfiles.cv },
              { key: 'github', title: 'GitHub', data: sourceProfiles.github },
              { key: 'linkedin', title: 'LinkedIn', data: sourceProfiles.linkedin },
            ].map(src => <article className={`card skill-source-card ${activeSource === src.key ? 'is-selected' : ''}`} key={src.key}>
              <div className="skill-source-card-top">
                <h3>{src.title}</h3>
                <span className={`skill-source-status status-${src.data?.status || 'not_provided'}`}>{(src.data?.status || 'not_provided').replaceAll('_', ' ')}</span>
              </div>
              <strong>{src.data?.skill_count ?? 0} skills</strong>
              <p>{src.data?.status === 'completed' ? 'Independently analysed source profile.' : 'Unavailable or not provided — never penalizes CV.'}</p>
              <button type="button" className={activeSource === src.key ? '' : 'button-secondary'} onClick={() => { setActiveSource(src.key); setActiveCategory('All') }}>
                View {src.title}
              </button>
            </article>)}
          </section>}

          <section className="card sp-inventory-header" aria-label="Skill inventory filters">
            <div className="sp-inventory-top">
              <div>
                <h3>Assessed Skills ({visibleSkills.length})</h3>
                <p className="sp-muted">Click "Technical details, XAI & evidence" on any skill to inspect supporting evidence and score factors.</p>
              </div>
              <div className="sp-filter-controls">
                {sourceProfiles && <button type="button" className={activeSource === 'combined' ? '' : 'button-secondary'} onClick={() => { setActiveSource('combined'); setActiveCategory('All') }}>
                  Combined ({allCombinedSkills.length})
                </button>}
                {hasOtherSkills && <button type="button" className={domainView === 'relevant' ? '' : 'button-secondary'} onClick={() => setDomainView(v => v === 'relevant' ? 'all' : 'relevant')}>
                  {domainView === 'relevant' ? `Showing ${primaryDomain} (${relevantSkills.length})` : `Showing All (${baseSkills.length})`}
                </button>}
              </div>
            </div>
            {categories.length > 2 && <div className="skill-category-bar" role="group" aria-label="Filter by skill category">
              {categories.map(cat => <button key={cat} type="button" className={`skill-cat-pill ${activeCategory === cat ? 'is-active' : ''}`} onClick={() => setActiveCategory(cat)}>{cat}</button>)}
            </div>}
          </section>

          {visibleSkills.length === 0 ? <div className="card"><h3>No skills in this view</h3><p className="sp-muted">No skills were extracted for the selected source or category filter.</p></div> : <div className="skill-results-grid">{visibleSkills.map(skill => {
            const pct = skillPct(skill)
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
                <span className="skill-level">{pct}% <small>Lv {skill.level}/5</small></span>
              </div>

              <div className="skill-progress-track" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={`${skill.name} estimated proficiency ${pct}%`}>
                <div className="skill-progress-fill" style={{ width: `${pct}%` }} />
              </div>

              <p className="skill-confidence">
                {skill.proficiency_label || 'Provisional'} · {skill.confidence} confidence · {skill.status.replaceAll('_', ' ')}
              </p>
              <p className="sp-reason">{skill.reason}</p>

              <details className="skill-xai-box">
                <summary>Technical details, XAI & evidence ({skill.evidence.length})</summary>
                {!!skill.occupations?.length && <div className="skill-domain-tags">{skill.occupations.slice(0, 5).map(occ => <span key={occ} className={`skill-domain-tag ${occ === primaryOccupation ? 'is-primary' : ''}`}>{occ}</span>)}</div>}
                {xai && <>
                  <p className="xai-why"><strong>Why identified:</strong> {xai.why_identified}</p>
                  <p className="xai-type"><strong>Evidence basis:</strong> {xai.self_reported_only ? 'Self-reported only' : (xai.evidence_types || []).join(', ').replaceAll('_', ' ')}</p>
                  {!!xai.score_factors?.length && <ul className="xai-factors">{xai.score_factors.map((f, idx) => <li key={idx}><strong>{f.factor} (+{f.points}%):</strong> {f.detail}</li>)}</ul>}
                  {!!xai.evidence_limitations?.length && <p className="xai-limits"><strong>Limitations:</strong> {xai.evidence_limitations.join(' ')}</p>}
                </>}
                {skill.evidence.map((evidence, index) => <blockquote key={index}><small>{evidence.section}{evidence.match_method ? ` · ${evidence.match_method.replaceAll('_', ' ')}` : ''}{typeof evidence.semantic_similarity === 'number' ? ` · sim ${evidence.semantic_similarity.toFixed(2)}` : ''}</small>{evidence.text}</blockquote>)}
              </details>
            </article>
          })}</div>}

          {comparison && <details className="card sp-expandable">
            <summary>
              <span>Cross-source skill comparison</span>
              <small>{comparison.summary?.multi_source_count ?? 0} multi-source · {comparison.summary?.single_source_count ?? 0} single-source · {comparison.summary?.claimed_vs_practical_gap_count ?? 0} claimed only</small>
            </summary>
            <div className="sp-expand-body">
              <p className="skill-multi-note">{comparison.summary?.note}</p>
              <div className="skill-category-bar" role="group" aria-label="Filter cross-source comparison">
                {[
                  { key: 'all', label: `All (${comparison.summary?.total_compared_skills ?? 0})` },
                  { key: 'multi', label: `Multiple sources (${comparison.summary?.multi_source_count ?? 0})` },
                  { key: 'single', label: `Single source (${comparison.summary?.single_source_count ?? 0})` },
                  { key: 'gaps', label: `Claimed vs practical (${comparison.summary?.claimed_vs_practical_gap_count ?? 0})` },
                ].map(f => <button key={f.key} type="button" className={`skill-cat-pill ${compareFilter === f.key ? 'is-active' : ''}`} onClick={() => setCompareFilter(f.key)}>{f.label}</button>)}
              </div>
              <div className="skill-compare-list">
                {comparedSkills.map(item => <div className="skill-compare-row" key={item.name}>
                  <div className="skill-compare-main">
                    <strong>{item.name}</strong>
                    <span className={`skill-claim-badge claim-${item.claim_vs_practice_status}`}>{CLAIM_LABELS[item.claim_vs_practice_status] || item.claim_vs_practice_status}</span>
                    <p>{item.discrepancy_note}</p>
                  </div>
                  <div className="skill-compare-sources">
                    {['cv', 'github', 'linkedin'].map(src => {
                      const detail = item.source_details?.[src]
                      return <span key={src} className={`compare-source-pill ${detail?.present ? 'is-present' : 'is-absent'}`}>
                        {src.toUpperCase()}: {detail?.present ? `${detail.percentage ?? detail.level * 20}%` : '—'}
                      </span>
                    })}
                  </div>
                </div>)}
              </div>
            </div>
          </details>}

          {!!result.external_profiles?.length && <details className="card sp-expandable">
            <summary>
              <span>Detected profile identifiers ({result.external_profiles.length})</span>
              <small>Unverified links found in CV</small>
            </summary>
            <div className="sp-expand-body skill-profile-links">
              <p>Identifiers only. Ownership has not been verified.</p>
              {result.external_profiles.map(profile => <a key={profile.platform} href={profile.url} target="_blank" rel="noopener noreferrer">{profile.platform === 'github' ? 'GitHub' : 'LinkedIn'}: {profile.handle} <Icon name="arrow" size={15} /></a>)}
            </div>
          </details>}

          <details className="card sp-expandable">
            <summary>
              <span>Technical metadata, domain signals & warnings</span>
              <small>{result.assessment_method} · {result.model_version}</small>
            </summary>
            <div className="sp-expand-body skill-method">
              {!!domain?.signals?.length && <>
                <p><strong>Domain detection signals:</strong></p>
                <ul className="skill-domain-signals">{domain.signals.map((signal, index) => <li key={index}>{signal}</li>)}</ul>
              </>}
              {result.warnings.map((warning, index) => <p key={index}>{warning}</p>)}
            </div>
          </details>
        </div>
      </details>
    </>}
  </div>
}
