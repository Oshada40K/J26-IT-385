// Pure helpers for the Home page (no React, no browser APIs) so they run under node --test.

export function greeting(date = new Date()) {
  const hour = date.getHours()
  return hour < 5 ? 'Good evening' : hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'
}

export const firstName = fullName => (fullName || '').trim().split(/\s+/)[0] || ''

// The Home filter chips group the 27 tracked careers. Unknown careers fall under Engineering.
export const CAREER_CATEGORIES = {
  'Data & AI': ['Machine Learning / AI Engineer', 'Data Scientist', 'Data Engineer', 'Data Analyst', 'Database Administrator'],
  Security: ['Cybersecurity Specialist'],
  Business: ['Product Manager', 'IT Project Manager', 'Business / Systems Analyst', 'ERP / CRM Consultant', 'IT Consultant', 'Technical Writer', 'UI/UX Designer'],
}
export const CATEGORY_NAMES = ['Engineering', ...Object.keys(CAREER_CATEGORIES)]

export function categoryOf(career) {
  return Object.keys(CAREER_CATEGORIES).find(name => CAREER_CATEGORIES[name].includes(career)) || 'Engineering'
}

// Sorts a copy; careers without a growth figure always go last when sorting by growth.
export function sortCareers(careers, key) {
  const list = [...careers]
  if (key === 'new') return list.sort((a, b) => b.new_postings - a.new_postings || a.rank - b.rank)
  if (key === 'growth') {
    return list.sort((a, b) => {
      const x = a.growth?.pct, y = b.growth?.pct
      if (x == null && y == null) return a.rank - b.rank
      if (x == null) return 1
      if (y == null) return -1
      return y - x || a.rank - b.rank
    })
  }
  return list.sort((a, b) => a.rank - b.rank)
}

const normal = text => (text || '').toLowerCase().replace(/[^a-z0-9+#]+/g, '')

// Market skill names that differ from how a CV usually names the same skill.
const SKILL_ALIASES = {
  'Generative AI / LLMs': ['generativeai', 'genai', 'llm', 'llms', 'largelanguagemodels'],
  'CI/CD': ['cicd', 'continuousintegration'],
  'HTML/CSS': ['html', 'css', 'html5', 'css3'],
  'Node.js': ['nodejs', 'node'],
  'Vue.js': ['vuejs', 'vue'],
  'Google Cloud': ['googlecloud', 'gcp', 'googlecloudplatform'],
  'AWS': ['aws', 'amazonwebservices'],
  '.NET': ['net', 'dotnet', 'aspnet'],
  'Golang': ['golang', 'go'],
  'REST APIs': ['restapi', 'restapis', 'rest', 'restful'],
  'Machine Learning': ['machinelearning', 'ml'],
  'Apache Spark': ['apachespark', 'spark', 'pyspark'],
  'PostgreSQL': ['postgresql', 'postgres'],
  'Kubernetes': ['kubernetes', 'k8s'],
  'Git': ['git', 'github', 'gitlab'],
}

// True when the student's CV skills include this market skill (exact name or a known alias).
export function hasSkill(marketSkill, cvSkills) {
  const wanted = new Set([normal(marketSkill), ...(SKILL_ALIASES[marketSkill] || [])])
  return cvSkills.some(skill => wanted.has(normal(skill)))
}

// Change between the last two days that both have a value; null when there is no earlier day.
export function previousDelta(points, field) {
  const values = points.filter(point => point[field] != null)
  if (values.length < 2) return null
  const current = values[values.length - 1][field]
  const before = values[values.length - 2][field]
  return { value: current - before, pct: before ? Math.round(((current - before) / before) * 1000) / 10 : null, since: values[values.length - 2] }
}

// Same checks and messages as before the redesign: which file problem to report, or ''.
export function fileProblem(files) {
  if (files.length > 1) return 'Please choose one CV at a time.'
  const selected = files[0]
  if (!/\.(pdf|docx)$/i.test(selected.name)) return 'Please choose a PDF or DOCX file.'
  if (!selected.size || selected.size > 10 * 1024 * 1024) return 'Choose a file between 1 byte and 10 MB.'
  return ''
}
