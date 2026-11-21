// Owner: Oshada - Component 03: Explainable Career Recommendation.
// Loads the three career APIs and presents them as one result view. The backend
// builds the recommendation from the Component 01 and 02 profiles for the saved candidate.
// Page sections (c3Sections.jsx): best-match hero + gauge, why + SHAP factors, skills,
// what-if (single skill changes), other paths, confidence, top 5, method. The data loading
// below is unchanged; the redesign is presentation only.
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import Icon from '../../components/Icon.jsx'
import { useInViewport } from '../home/viewport.js'
import { gainsByTechnology, isTechnicalFactor } from './c3Model.js'
import { ConfidenceSection, Hero, MethodSection, PathsSection, SkillsSection, TopJobsSection, WhatIfSection, WhySection } from './c3Sections.jsx'
import { API_BASE_URL } from '../../api/client.js'
import { savedSession } from '../component01/skillApi.js'
import { ENDPOINTS, describeCareerError, getCareerInsights, getCareerResult } from './careerApi.js'
import { PageLoader, ReloadButton, SkeletonCareer, Spinner } from '../../components/loading/index.js'
import { cached, candidateKey, hasCached, peek, prime } from '../../api/resourceCache.js'
import './CareerRecommendation.css'

const emptyState = { loading: false, data: null, error: null }
const cacheKey = (key) => candidateKey(`c03:${key}`)
const INSIGHTS_KEY = 'insights'

export default function CareerRecommendation() {
  const location = useLocation()
  const [prediction] = useState(() => {
    const state = location.state
    return state?.candidateId === savedSession()?.candidate_id && state?.careerResults ? state.careerResults : null
  })
  const [fresh] = useState(() => !Object.keys(ENDPOINTS).some((key) => hasCached(cacheKey(key))))
  // Results passed from the CV upload, else the last results seen on this page, else nothing yet.
  const [results, setResults] = useState(() => prediction || Object.fromEntries(Object.keys(ENDPOINTS).map((key) =>
    [key, hasCached(cacheKey(key)) ? { ...emptyState, data: peek(cacheKey(key)) } : emptyState])))
  const [insights, setInsights] = useState(() =>
    hasCached(cacheKey(INSIGHTS_KEY)) ? { ...emptyState, data: peek(cacheKey(INSIGHTS_KEY)) } : emptyState)

  async function load(key) {
    setResults((prev) => ({ ...prev, [key]: { ...prev[key], loading: true, error: null } }))
    try {
      const data = await cached(cacheKey(key), () => getCareerResult(key, API_BASE_URL, savedSession()))
      setResults((prev) => ({ ...prev, [key]: { loading: false, data, error: null } }))
    } catch (err) {
      // Keep results already on screen; the error banner offers a retry.
      setResults((prev) => ({ ...prev, [key]: { loading: false, data: prev[key].data, error: describeCareerError(err, API_BASE_URL) } }))
    }
  }

  // The insights API is slower (about 60 extra model passes), so it has its own state and
  // never blocks the core result view. Failures here only hide the insight cards.
  async function loadInsights() {
    setInsights((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const data = await cached(cacheKey(INSIGHTS_KEY), () => getCareerInsights(API_BASE_URL, savedSession()))
      setInsights({ loading: false, data, error: null })
    } catch (err) {
      setInsights((prev) => ({ loading: false, data: prev.data, error: describeCareerError(err, API_BASE_URL) }))
    }
  }

  const loadAll = () => Promise.all([...Object.keys(ENDPOINTS).map(load), loadInsights()])
  const states = Object.values(results)
  const anyLoading = states.some((r) => r.loading)
  const errors = [...new Set(states.map((r) => r.error).filter(Boolean))]

  // Load automatically unless results were passed from the CV upload (those are cached for later
  // visits). Cached results stay on screen while they are refreshed in the background.
  useEffect(() => {
    if (prediction) {
      Object.entries(prediction).forEach(([key, r]) => { if (r.data) prime(cacheKey(key), r.data) })
      loadInsights()
    } else loadAll()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const best = results.bestJob.data
  const top = results.topJobs.data
  const why = results.explanation.data
  const metadata = best || top || why
  const isSample = !savedSession()?.candidate_id
  // Only show insights that belong to the recommendation on screen.
  const extra = insights.data && (!metadata || insights.data.candidate_id === metadata.candidate_id) ? insights.data : null

  // Interactions: what-if preview on the gauge, factor -> reason highlight, chip -> what-if row.
  const heroRef = useRef(null)
  const [hovered, setHovered] = useState(null)
  const [pinned, setPinned] = useState(null)
  const [focus, setFocus] = useState(null)
  const [flash, setFlash] = useState(null)
  const preview = hovered || pinned
  const reduced = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const scrollTo = useCallback(id => document.getElementById(id)?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' }), [reduced])
  function showSkill(skill) {
    const row = document.querySelector(`#c3-whatif [data-technology="${CSS.escape(skill)}"]`)
    if (row) { row.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'center' }); setFlash(skill); setTimeout(() => setFlash(null), 1800) }
    else scrollTo('c3-whatif')
  }
  const busy = anyLoading || insights.loading

  return (
    <div className={`page accent-career c3-page ${busy && metadata ? 'is-refreshing' : ''}`} aria-busy={busy}>
      <div className="c3-header">
        <div>
          <p className="eyebrow">COMPONENT 03 / EXPLAINABLE CAREER INTELLIGENCE</p>
          <h1 className="c3-title" aria-label="Find your direction. Understand why.">
            {'Find your direction. Understand why.'.split(' ').map((word, index) => <span key={index} className="c3-word" aria-hidden="true"><span style={{ '--i': index }}>{word}</span></span>)}
          </h1>
          <p className="page-description">Your strongest career match, five ranked possibilities, and the evidence behind the recommendation.</p>
          {!isSample && <span className="c3-pill">● Based on your CV skills and personality profile</span>}
        </div>
        <ReloadButton className="c3-refresh" onClick={loadAll} loading={busy} loadingLabel="Analysing…" />
      </div>

      {isSample && <div className="c3-sample" role="note">
        <span className="c3-sample-icon"><Icon name="alert" size={18} /></span>
        <div><strong>You are looking at a sample profile.</strong><p>Upload your CV in Skill assessment to personalise these recommendations.</p></div>
        <Link to="/component01" className="c3-sample-button">Upload your CV <Icon name="arrow" size={15} /></Link>
      </div>}

      {errors.map((error) => (
        <div className="c3-error fx-reveal" role="alert" key={error}>
          <span>{error}</span>
          <ReloadButton onClick={loadAll} loading={anyLoading} label="Try again" loadingLabel="Retrying…" />
        </div>
      ))}

      {anyLoading && !metadata && <PageLoader variant="career" label="Finding your best career matches…" skeleton={<SkeletonCareer />} />}

      {metadata && <SectionNav heroRef={heroRef} onGo={scrollTo} hasWhy={Boolean(why)} hasInsights={Boolean(extra)} hasTop={Boolean(top)} />}

      <div className={fresh ? 'fx-stagger' : undefined}>
        {(best || top) && (
          <Hero
            heroRef={heroRef}
            title={best?.best_job || top.jobs[0].job}
            score={why?.match_score ?? top?.jobs[0].score}
            occupations={metadata.eligible_occupations}
            matchedCount={why?.matched_technologies.length || 0}
            skills={why?.matched_technologies || []}
            uncertainty={extra?.uncertainty}
            meaning={metadata.score_meaning}
            preview={preview}
            onWhy={() => scrollTo('c3-why')}
          />
        )}

        {why && (
          <>
            <WhySection reasons={why.key_reasons} factors={why.factors} shapText={why.explanation.split(/(?<=\.)\s+/).filter(Boolean)} focus={focus} onFocus={setFocus} />
            <SkillsSection matched={why.matched_technologies} toLearn={why.skills_to_learn} gains={gainsByTechnology(extra?.counterfactuals?.actions)}
              target={extra?.counterfactuals?.target || best?.best_job} highlightMatched={Boolean(focus && isTechnicalFactor(focus))} onLearn={showSkill} />
          </>
        )}

        {metadata && !extra && insights.loading && (
          <div className="c3-card c3-full c3-insights-pending" role="status">
            <Spinner /> <span>Computing what-if scenarios and confidence ranges…</span>
          </div>
        )}
        {metadata && !extra && insights.error && !insights.loading && (
          <div className="c3-error fx-reveal" role="alert">
            <span>Insights unavailable: {insights.error}</span>
            <ReloadButton onClick={loadInsights} loading={insights.loading} label="Retry insights" loadingLabel="Retrying…" />
          </div>
        )}

        {extra && (
          <>
            <div className="c3-grid">
              <WhatIfSection cf={extra.counterfactuals} preview={preview} pinned={pinned} flash={flash}
                onHover={setHovered} onPin={action => setPinned(current => current?.technology === action.technology ? null : action)} />
              <PathsSection cf={extra.counterfactuals} />
            </div>
            <ConfidenceSection unc={extra.uncertainty} stability={extra.explanation_stability} />
          </>
        )}

        {top && <TopJobsSection jobs={top.jobs} />}

        {best?.unrecognised_skills?.length > 0 && (
          <p className="c3-note c3-unrecognised">
            Not used in matching (not in the O*NET skill catalogue): {best.unrecognised_skills.join(', ')}
          </p>
        )}

        {metadata && <MethodSection data={metadata} />}
      </div>
    </div>
  )
}

// Sticky section pills, shown once the hero has scrolled away. The active pill follows scroll.
function SectionNav({ heroRef, onGo, hasWhy, hasInsights, hasTop }) {
  const heroVisible = useInViewport(heroRef)
  const items = [
    ['c3-best', 'Best match', true], ['c3-why', 'Why', hasWhy], ['c3-skills', 'Skills', hasWhy], ['c3-whatif', 'What-if', hasInsights],
    ['c3-paths', 'Other paths', hasInsights], ['c3-confidence', 'Confidence', hasInsights], ['c3-top5', 'Top 5', hasTop], ['c3-method', 'Method', true],
  ].filter(([, , shown]) => shown)
  const ids = items.map(([id]) => id).join()
  const [active, setActive] = useState(items[0][0])
  useEffect(() => {
    let frame = 0
    const list = ids.split(',')
    const update = () => {
      frame = 0
      let current = list[0]
      for (const id of list) { const el = document.getElementById(id); if (el && el.getBoundingClientRect().top <= 160) current = id }
      setActive(current)
    }
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(update) }
    update()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => { window.removeEventListener('scroll', onScroll); cancelAnimationFrame(frame) }
  }, [ids])
  const shown = Boolean(heroRef.current) && !heroVisible
  return <nav className={`c3-section-nav ${shown ? 'is-shown' : ''}`} aria-label="Sections on this page" aria-hidden={!shown}>
    {items.map(([id, label]) => <button key={id} type="button" tabIndex={shown ? 0 : -1} className={active === id ? 'is-active' : ''}
      aria-current={active === id ? 'true' : undefined} onClick={() => onGo(id)}>{label}</button>)}
  </nav>
}
