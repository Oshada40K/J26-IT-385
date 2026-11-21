// Destinations offered by the command palette (pure data + filtering, testable with node --test).
export const PALETTE_ITEMS = [
  { id: 'home', group: 'Modules', label: 'Home', hint: 'Upload your CV and see the job market', to: '/', icon: 'home' },
  { id: 'c01', group: 'Modules', label: 'Skill assessment', hint: '01 · Technical skills from your CV', to: '/component01', icon: 'skill' },
  { id: 'c02', group: 'Modules', label: 'Personality analysis', hint: '02 · Questionnaire, scenarios and writing', to: '/component02', icon: 'personality' },
  { id: 'c03', group: 'Modules', label: 'Career prediction', hint: '03 · Explainable career matches', to: '/component03', icon: 'career' },
  { id: 'c04', group: 'Modules', label: 'Learning roadmap', hint: '04 · Readiness and skill gaps', to: '/component04', icon: 'roadmap' },
  { id: 'profile', group: 'Modules', label: 'My profile', hint: 'Your details, account and privacy', to: '/profile', icon: 'document' },
  { id: 'api', group: 'Modules', label: 'API integration', hint: 'Check the backend APIs', to: '/api-test', icon: 'pulse' },
  { id: 'upload', group: 'On the Home page', label: 'Upload your CV', hint: 'Start your assessment', section: 'cv-upload', icon: 'upload' },
  { id: 'pulse', group: 'On the Home page', label: 'Career Market Pulse', hint: 'Live job-market overview', section: 'market-pulse', icon: 'pulse' },
  { id: 'trending', group: 'On the Home page', label: 'Trending careers', hint: 'Careers ranked by open listings', section: 'trending-careers', icon: 'career' },
  { id: 'skills', group: 'On the Home page', label: 'Skill demand', hint: 'Most requested technical skills', section: 'skill-demand', icon: 'skill' },
  { id: 'salary', group: 'On the Home page', label: 'Salary insights', hint: 'Median disclosed pay by career', section: 'salary-insights', icon: 'document' },
  { id: 'sources', group: 'On the Home page', label: 'Data sources', hint: 'Where the market data comes from', section: 'data-sources', icon: 'document' },
]

// Every typed word must appear in the label, hint or group (case-insensitive).
export function filterItems(items, query) {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  return items.filter(item => words.every(word => `${item.label} ${item.hint} ${item.group}`.toLowerCase().includes(word)))
}

export const shortcutLabel = (platform = typeof navigator === 'undefined' ? '' : navigator.platform || navigator.userAgent || '') =>
  (/Mac|iPhone|iPad/.test(platform) ? '⌘K' : 'Ctrl K')
