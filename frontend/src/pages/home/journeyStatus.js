// Pure rules for the journey statuses (no browser APIs, so they run under node --test).
export const STEPS = [
  { key: 'c01', number: '01', label: 'Skill assessment', detail: 'Technical skills read from your CV', to: '/component01', icon: 'skill' },
  { key: 'c02', number: '02', label: 'Personality analysis', detail: 'Questionnaire, scenarios and writing', to: '/component02', icon: 'personality' },
  { key: 'c03', number: '03', label: 'Career prediction', detail: 'Explainable top-five career matches', to: '/component03', icon: 'career' },
  { key: 'c04', number: '04', label: 'Learning roadmap', detail: 'Readiness score and skill-gap plan', to: '/component04', icon: 'roadmap' },
]

export const STATUS_LABELS = { done: 'Done', 'in-progress': 'In progress', ready: 'Ready', locked: 'Needs your CV' }

// Component 02 keeps its progress as a draft: each of its three parts is stored once scored.
export function personalityStatus(draft) {
  if (!draft || typeof draft !== 'object') return 'ready'
  const parts = ['questionnaire', 'sjt', 'writing']
  if (parts.every(part => draft[part])) return 'done'
  const answered = parts.some(part => draft[part])
    || ['likert', 'choices', 'text'].some(field => draft[field] && Object.values(draft[field]).some(value => value !== '' && value != null))
  return answered ? 'in-progress' : 'ready'
}

// Career predictions are generated from the assessed CV, so step 03 is complete with step 01.
// The roadmap counts as done once a readiness assessment has been saved.
export function deriveStatuses({ cvAssessed, personality, roadmapDone }) {
  return {
    c01: cvAssessed ? 'done' : 'ready',
    c02: personality,
    c03: cvAssessed ? 'done' : 'locked',
    c04: roadmapDone ? 'done' : 'ready',
  }
}

// The first step that is neither done nor locked: the one to suggest next.
export function nextStep(statuses) {
  return STEPS.find(step => !['done', 'locked'].includes(statuses[step.key])) || null
}

export const completedCount = statuses => STEPS.filter(step => statuses[step.key] === 'done').length
