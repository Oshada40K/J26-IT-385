// Real progress through the four research components, for the Home journey stepper and the
// sidebar check marks. Read-only: it uses the components' existing APIs and saved state and
// never writes to them. A status that cannot be confirmed is never reported as "done".
import { useSyncExternalStore } from 'react'
import { candidateKey, reuse } from '../../api/resourceCache.js'
import { getSkillDetails, savedSession } from '../component01/skillApi.js'
import { findLatestAssessment } from '../component04/assessmentApi.js'
import { personalityStatus, deriveStatuses } from './journeyStatus.js'

export { STEPS, nextStep, personalityStatus, deriveStatuses } from './journeyStatus.js'

const PERSONALITY_DRAFT_KEY = 'careernova-personality-draft' // Component 02's own saved progress
const EMPTY = { loaded: false, candidateId: null, statuses: deriveStatuses({ cvAssessed: false, personality: 'ready', roadmapDone: false }), cvSkills: [] }

let state = EMPTY
let pending = null
const listeners = new Set()

function set(next) {
  state = next
  listeners.forEach(listener => listener())
}

function readPersonalityDraft() {
  try { return JSON.parse(sessionStorage.getItem(PERSONALITY_DRAFT_KEY) || 'null') }
  catch { return null }
}

// Re-reads every component's state. Failures count as "not confirmed", never as done.
export function refreshJourney() {
  if (pending) return pending
  pending = (async () => {
    const session = savedSession()
    let details = null
    if (session?.access_token) {
      try { details = await reuse(candidateKey('c01:details'), getSkillDetails) } catch { details = null }
    }
    let roadmap = null
    try { roadmap = await findLatestAssessment() } catch { roadmap = null }
    set({
      loaded: true,
      candidateId: session?.candidate_id || null,
      cvSkills: (details?.skills || []).map(skill => skill.name).filter(Boolean),
      statuses: deriveStatuses({ cvAssessed: Boolean(details), personality: personalityStatus(readPersonalityDraft()), roadmapDone: Boolean(roadmap) }),
    })
  })().finally(() => { pending = null })
  return pending
}

// A CV was just assessed and careers predicted on Home, so steps 01 and 03 are complete.
export function markCvAssessed(candidateId) {
  set({ ...state, loaded: true, candidateId, statuses: { ...state.statuses, c01: 'done', c03: 'done' } })
}

function subscribe(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
const snapshot = () => state

// The store belongs to one candidate: after a logout or a new account it reads as empty.
export function useJourney() {
  const current = useSyncExternalStore(subscribe, snapshot, snapshot)
  const candidateId = savedSession()?.candidate_id || null
  return current.loaded && current.candidateId === candidateId ? current : { ...EMPTY, loaded: current.loaded }
}
