// Pure rules for the profile page (no browser APIs, so they run under node --test).

export const ACADEMIC_YEARS = ['Year 1', 'Year 2', 'Year 3', 'Year 4', 'Postgraduate', 'Graduate']
export const WORK_TYPES = [{ value: 'remote', label: 'Remote' }, { value: 'hybrid', label: 'Hybrid' }, { value: 'onsite', label: 'On-site' }]
export const REGIONS = [{ value: 'sri_lanka', label: 'Sri Lanka' }, { value: 'remote', label: 'Remote' }, { value: 'global', label: 'Global' }]
export const INTERESTS = [
  'Software Engineering', 'Web Development', 'Mobile Development', 'Data Science', 'Data Analytics',
  'Machine Learning / AI', 'Cybersecurity', 'Cloud & DevOps', 'UI/UX Design', 'Quality Assurance',
  'Business Analysis', 'Project Management', 'Networking', 'Game Development',
]
export const MAX_INTERESTS = 10
export const BIO_LIMIT = 300
export const MAX_PHOTO_BYTES = 2 * 1024 * 1024

export const FORM_FIELDS = ['full_name', 'phone', 'location', 'university', 'degree', 'academic_year', 'graduation_year',
  'linkedin_url', 'github_url', 'bio', 'interests', 'work_type', 'region']

// The editable form state from a saved profile (null values become empty inputs).
export function formFrom(profile = {}) {
  const form = {}
  for (const field of FORM_FIELDS) form[field] = field === 'interests' ? [...(profile.interests || [])] : profile[field] ?? ''
  form.graduation_year = profile.graduation_year ? String(profile.graduation_year) : ''
  return form
}

export function isDirty(form, saved) {
  return JSON.stringify(form) !== JSON.stringify(saved)
}

// The request body: trimmed strings, empty optional fields as null.
export function payloadFrom(form) {
  const text = value => (typeof value === 'string' ? value.trim() : value) || null
  return {
    full_name: form.full_name.trim(), phone: text(form.phone), location: text(form.location), university: text(form.university),
    degree: text(form.degree), academic_year: text(form.academic_year),
    graduation_year: form.graduation_year ? Number(form.graduation_year) : null,
    linkedin_url: text(form.linkedin_url), github_url: text(form.github_url), bio: text(form.bio),
    interests: form.interests, work_type: text(form.work_type), region: text(form.region),
  }
}

// Same rules as the backend (backend/app/auth/profile.py), shown inline before saving.
export function validate(form, thisYear = new Date().getFullYear()) {
  const errors = {}
  const name = form.full_name.trim()
  if (name.length < 2) errors.full_name = 'Enter your full name.'
  else if (name.length > 100) errors.full_name = 'Use 100 characters or fewer.'
  if (form.phone.trim() && !/^\+?[0-9][0-9 ()-]{6,18}$/.test(form.phone.trim())) errors.phone = 'Enter a phone number with digits only, for example +94 77 123 4567.'
  if (form.graduation_year) {
    const year = Number(form.graduation_year)
    if (!Number.isInteger(year) || year < 1990 || year > 2100) errors.graduation_year = 'Enter a year between 1990 and 2100.'
    else if (year > thisYear + 8) errors.graduation_year = `That is more than 8 years away. Check the year.`
  }
  if (form.linkedin_url.trim() && !/^https:\/\/([a-z]{2,3}\.)?linkedin\.com\/\S+$/i.test(form.linkedin_url.trim())) errors.linkedin_url = 'Use a link that starts with https://www.linkedin.com/'
  if (form.github_url.trim() && !/^https:\/\/(www\.)?github\.com\/[A-Za-z0-9-]+\/?$/.test(form.github_url.trim())) errors.github_url = 'Use a link like https://github.com/your-username'
  if (form.bio.length > BIO_LIMIT) errors.bio = `Keep your bio to ${BIO_LIMIT} characters.`
  for (const [field, limit] of [['location', 100], ['university', 120], ['degree', 120]]) {
    if (form[field].trim().length > limit) errors[field] = `Use ${limit} characters or fewer.`
  }
  return errors
}

// Completeness counts real filled fields and completed modules only.
export function completeness({ profile = {}, hasPhoto = false, statuses = {} }) {
  const items = [
    { key: 'photo', label: 'Add a profile photo', done: hasPhoto },
    { key: 'university', label: 'Add your university', done: Boolean(profile.university) },
    { key: 'degree', label: 'Add your degree programme', done: Boolean(profile.degree) },
    { key: 'year', label: 'Add your academic and graduation year', done: Boolean(profile.academic_year && profile.graduation_year) },
    { key: 'location', label: 'Add your location', done: Boolean(profile.location) },
    { key: 'bio', label: 'Write a short bio', done: Boolean(profile.bio) },
    { key: 'interests', label: 'Choose your career interests', done: (profile.interests || []).length > 0 },
    { key: 'preferences', label: 'Set your preferred work type and region', done: Boolean(profile.work_type && profile.region) },
    { key: 'links', label: 'Add your LinkedIn or GitHub link', done: Boolean(profile.linkedin_url || profile.github_url) },
    { key: 'c01', label: 'Complete the skill assessment', done: statuses.c01 === 'done', module: true },
    { key: 'c02', label: 'Complete the personality analysis', done: statuses.c02 === 'done', module: true },
    { key: 'c03', label: 'Get your career prediction', done: statuses.c03 === 'done', module: true },
    { key: 'c04', label: 'Build your learning roadmap', done: statuses.c04 === 'done', module: true },
  ]
  const done = items.filter(item => item.done).length
  return { percent: Math.round((done / items.length) * 100), done, total: items.length, missing: items.filter(item => !item.done) }
}

// 0-4 with a label. The backend requires at least 12 characters, so shorter is always "Too short".
export function passwordStrength(password) {
  if (!password) return { score: 0, label: '' }
  if (password.length < 12) return { score: 0, label: 'Too short' }
  let score = 1
  if (password.length >= 16) score += 1
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1
  if (/\d/.test(password) && /[^A-Za-z0-9]/.test(password)) score += 1
  if (/^(.)\1+$/.test(password) || /^(?:password|123456|qwerty)/i.test(password)) score = 1
  return { score, label: ['Too short', 'Weak', 'Fair', 'Good', 'Strong'][score] }
}

// ---------- Module summaries (inputs come from the modules' own APIs and saved state) ----------

export const TRAITS = [
  { code: 'OPN', name: 'Openness', high: 'Curious, enjoys new ideas', low: 'Practical, prefers the familiar' },
  { code: 'CON', name: 'Conscientiousness', high: 'Organised and dependable', low: 'Flexible, spontaneous' },
  { code: 'EXT', name: 'Extraversion', high: 'Energised by people', low: 'Prefers focused solo work' },
  { code: 'AGR', name: 'Agreeableness', high: 'Cooperative, empathetic', low: 'Direct, competitive' },
  { code: 'NEU', name: 'Neuroticism', high: 'Feels stress more easily', low: 'Calm under pressure' },
]

// Component 02 stores scored parts in its draft. Traits come from the questionnaire (0-1 levels),
// described the same way Component 02 does: only clearly high (>= 0.6) or low (<= 0.4) levels.
export function personalitySummary(draft) {
  const traits = draft?.questionnaire?.traits
  if (!traits) return null
  return TRAITS.filter(trait => typeof traits[trait.code] === 'number').map(trait => {
    const level = traits[trait.code]
    return { ...trait, level, note: level >= 0.6 ? trait.high : level <= 0.4 ? trait.low : 'Balanced' }
  })
}

export function topSkills(details, count = 8) {
  return [...(details?.skills || [])].filter(skill => skill?.name)
    .sort((a, b) => (b.level ?? 0) - (a.level ?? 0) || a.name.localeCompare(b.name)).slice(0, count)
}

// Roadmap progress from Component 04's analysis: the share of the career's skills already met.
export function roadmapProgress(analysis) {
  const skills = analysis?.skill_gaps?.skills || []
  if (!skills.length) return null
  const met = skills.filter(skill => ['met', 'ok'].includes(skill.status)).length
  const next = (analysis.roadmap?.stages || []).flatMap(stage => stage.steps || [])[0] || null
  return { percent: Math.round((met / skills.length) * 100), met, total: skills.length, next }
}

// The CV file name is only known when it was recorded at upload; it is shown only if it belongs
// to the latest assessment (recorded no earlier than 15 minutes before it).
export function cvName(cvRecord, assessedAt) {
  if (!cvRecord?.file_name || !cvRecord.uploaded_at) return null
  if (!assessedAt) return cvRecord.file_name
  return new Date(cvRecord.uploaded_at) >= new Date(new Date(assessedAt).getTime() - 15 * 60_000) ? cvRecord.file_name : null
}

export const initials = name => name?.split(/\s+/).filter(Boolean).map(part => part[0]).slice(0, 2).join('').toUpperCase() || 'CN'

export function photoProblem(file) {
  if (!file) return 'Choose a photo.'
  if (!['image/jpeg', 'image/png'].includes(file.type)) return 'Choose a JPG or PNG photo.'
  if (file.size > MAX_PHOTO_BYTES) return 'Choose a photo of 2 MB or less.'
  return ''
}
