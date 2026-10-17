// Owner: Dewmi - Component 04 page: Career Readiness Assessment form and explainable results.
import { useEffect, useState } from 'react'
import Icon from '../../components/Icon.jsx'
import CareerReadinessForm from './CareerReadinessForm.jsx'
import RoadmapResults from './RoadmapResults.jsx'
import { findLatestAssessment, getAssessment } from './assessmentApi.js'
import './CareerReadinessForm.css'

export default function LearningRoadmap() {
  // view: loading | form | results
  const [view, setView] = useState('loading')
  const [record, setRecord] = useState(null)

  useEffect(() => {
    let active = true
    findLatestAssessment()
      .then(latest => { if (active) { setRecord(latest); setView(latest ? 'results' : 'form') } })
      .catch(() => { if (active) setView('form') })
    return () => { active = false }
  }, [])

  async function handleSubmitted(saved) {
    setRecord(await getAssessment(saved.assessment_id).catch(() => ({ ...saved, form: record?.form })))
    setView('results')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function show(next, nextRecord = record) {
    setRecord(nextRecord)
    setView(next)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return <div className="page accent-roadmap c4-page">
    <div className="page-heading">
      <div>
        <p className="eyebrow">COMPONENT 04 / LEARNING ROADMAP & SKILL GAP</p>
        <h1>{view === 'results' ? 'Your learning roadmap' : 'Career Readiness Assessment'}</h1>
        <p className="page-description">{view === 'results'
          ? 'See how your CV evidence compares with your chosen career, which skills to focus on first, and a step-by-step plan to get there.'
          : 'Tell us how confident you feel with the key skills for your chosen career, how you like to learn, and the practical experience you already have.'}</p>
      </div>
      <span className="component-icon"><Icon name="roadmap" size={28} /></span>
    </div>
    {view === 'loading' && <div className="card" role="status">Loading…</div>}
    {view === 'form' && <CareerReadinessForm key={record?.assessment_id || 'new'} initialRecord={record}
      onSubmitted={handleSubmitted} onCancel={record ? () => show('results') : undefined} />}
    {view === 'results' && record && <RoadmapResults assessmentId={record.assessment_id}
      onEdit={() => show('form')} onNew={() => show('form', record ? { ...record, career_id: '', form: { ...record.form, confidence: [] } } : null)} />}
  </div>
}
