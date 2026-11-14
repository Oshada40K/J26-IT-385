// Read-only summaries of the four research modules for the profile, through the modules' own
// helpers and saved state (the same sources as the Home journey). Nothing here writes to them.
// A module without data for this user returns null, and the page shows an empty state.
import { useCallback, useEffect, useState } from 'react'
import { API_BASE_URL } from '../../api/client.js'
import { candidateKey, reuse } from '../../api/resourceCache.js'
import { getSkillDetails, savedSession } from '../component01/skillApi.js'
import { getCareerResult } from '../component03/careerApi.js'
import { findLatestAssessment, getAnalysis } from '../component04/assessmentApi.js'
import { personalitySummary, roadmapProgress, topSkills } from './profileModel.js'

const PERSONALITY_DRAFT_KEY = 'careernova-personality-draft' // Component 02's own saved progress

export function readPersonalityDraft() {
  try { return JSON.parse(sessionStorage.getItem(PERSONALITY_DRAFT_KEY) || 'null') }
  catch { return null }
}

async function skills() {
  if (!savedSession()?.access_token) return null
  const details = await reuse(candidateKey('c01:details'), getSkillDetails)
  return details ? { details, top: topSkills(details), assessedAt: details.created_at || null } : null
}

// Predictions exist only for an assessed CV. Without a CV session Component 03 would return its
// sample profile, which must never be shown as this user's result.
async function careers(hasCv) {
  const session = savedSession()
  if (!hasCv || !session?.access_token) return null
  const data = await reuse(candidateKey('c03:topJobs'), () => getCareerResult('topJobs', API_BASE_URL, session))
  return data?.jobs?.length ? { top: data.jobs.slice(0, 3), all: data.jobs } : null
}

async function roadmap() {
  const record = await findLatestAssessment()
  if (!record) return null
  let progress = null
  let analysisError = ''
  try { progress = roadmapProgress(await getAnalysis(record.assessment_id)) }
  catch (error) { analysisError = error.message }
  return { record, progress, analysisError }
}

const settle = promise => promise.then(value => ({ value, error: '' }), error => ({ value: null, error: error.message || 'Could not load this module.' }))

export function useModuleData() {
  const [state, setState] = useState({ loading: true })
  const load = useCallback(async () => {
    setState(previous => ({ ...previous, loading: true }))
    const c01 = await settle(skills())
    const [c03, c04] = await Promise.all([settle(careers(Boolean(c01.value))), settle(roadmap())])
    const draft = readPersonalityDraft()
    setState({ loading: false, c01, c02: { value: draft ? { draft, traits: personalitySummary(draft) } : null, error: '' }, c03, c04 })
  }, [])
  useEffect(() => { load() }, [load])
  return [state, load]
}
