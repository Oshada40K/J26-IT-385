// Owner: Dewmi - Component 04 page: Career Readiness Assessment form and explainable results.
import { useEffect, useState } from 'react'
import Icon from '../../components/Icon.jsx'
import { PageLoader, SkeletonRoadmap, SkeletonSkillGap } from '../../components/loading/index.js'
import CareerReadinessForm, { QUESTIONS_PREFIX, RECOMMENDED_KEY } from './CareerReadinessForm.jsx'
import RoadmapResults from './RoadmapResults.jsx'
import { findLatestAssessment, getAssessment } from './assessmentApi.js'
import { cached, candidateKey, hasCached, invalidate, peek, prime } from '../../api/resourceCache.js'
import './CareerReadinessForm.css'

export default function LearningRoadmap() {
  // The latest assessment only changes when one is submitted here (cached below) or after a new
  // CV upload (which clears the cache), so a revisit opens straight on the last view.
  const latestKey = candidateKey('c04:latest')
  // view: loading | form | results
  const [view, setView] = useState(() => hasCached(latestKey) ? (peek(latestKey) ? 'results' : 'form') : 'loading')
  const [record, setRecord] = useState(() => peek(latestKey) ?? null)

  useEffect(() => {
    if (hasCached(latestKey)) return undefined
    let active = true
    cached(latestKey, findLatestAssessment)
      .then(latest => { if (active) { setRecord(latest); setView(latest ? 'results' : 'form') } })
      .catch(() => { if (active) setView('form') })
    return () => { active = false }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleSubmitted(saved) {
    const next = await getAssessment(saved.assessment_id).catch(() => ({ ...saved, form: record?.form }))
    invalidate('c04:analysis:')
    prime(latestKey, next)
    setRecord(next)
    setView('results')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function show(next, nextRecord = record) {
    setRecord(nextRecord)
    setView(next)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Component 03 now recommends another career (or this is a legacy, student-chosen roadmap): open the form for
  // the current recommendation. Learning methods, hours and experience are kept; ratings are asked again because
  // the skills differ. The stored assessment is never changed; submitting creates a new one.
  function regenerate() {
    invalidate(candidateKey(RECOMMENDED_KEY))
    invalidate(QUESTIONS_PREFIX)
    show('form', record ? { ...record, form: { ...record.form, confidence: [] } } : null)
  }

  return <div className="page accent-roadmap c4-page">
    <div className="page-heading">
      <div>
        <p className="eyebrow">COMPONENT 04 / LEARNING ROADMAP & SKILL GAP</p>
        <h1>{view === 'results' ? 'Your learning roadmap' : 'Career Readiness Assessment'}</h1>
        <p className="page-description">{view === 'results'
          ? 'See how your CV evidence compares with the career Component 03 recommends for you, which skills to focus on first, and a step-by-step plan to get there.'
          : 'Tell us how confident you feel with the key skills for the career Component 03 recommends for you, how you like to learn, and the practical experience you already have.'}</p>
      </div>
      <span className="component-icon"><Icon name="roadmap" size={28} /></span>
    </div>
    {view === 'loading' && <PageLoader variant="roadmap" label="Loading your latest assessment…"
      messages={['Generating Your Learning Roadmap…', 'Loading your latest assessment…', 'Checking your CV evidence…']}
      skeleton={<div className="sk-stack"><SkeletonSkillGap rows={3} /><SkeletonRoadmap /></div>} />}
    {view === 'form' && <CareerReadinessForm key={record?.assessment_id || 'new'} initialRecord={record}
      onSubmitted={handleSubmitted} onCancel={record ? () => show('results') : undefined} />}
    {view === 'results' && record && <RoadmapResults assessmentId={record.assessment_id}
      onEdit={() => show('form')} onRegenerate={regenerate} />}
  </div>
}
