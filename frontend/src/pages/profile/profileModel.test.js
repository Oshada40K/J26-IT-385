import test from 'node:test'
import assert from 'node:assert/strict'
import { completeness, cvName, formFrom, isDirty, passwordStrength, payloadFrom, personalitySummary, photoProblem, roadmapProgress, topSkills, validate } from './profileModel.js'

const filled = () => ({ ...formFrom({ full_name: 'Ada Lovelace' }) })

test('validation mirrors the backend rules', () => {
  assert.deepEqual(validate(filled(), 2026), {})
  const errors = validate({ ...filled(), full_name: ' ', phone: 'call me', graduation_year: '1800', linkedin_url: 'https://example.com', github_url: 'github.com/x', bio: 'x'.repeat(301) }, 2026)
  assert.deepEqual(Object.keys(errors).sort(), ['bio', 'full_name', 'github_url', 'graduation_year', 'linkedin_url', 'phone'])
  assert.equal(validate({ ...filled(), github_url: 'https://github.com/ada-l' }, 2026).github_url, undefined)
})

test('payload trims and turns empty optional fields into null', () => {
  const body = payloadFrom({ ...filled(), phone: '  ', graduation_year: '2027', university: ' SLIIT ' })
  assert.equal(body.phone, null)
  assert.equal(body.graduation_year, 2027)
  assert.equal(body.university, 'SLIIT')
})

test('dirty tracking compares the whole form', () => {
  const saved = filled()
  assert.equal(isDirty(filled(), saved), false)
  assert.equal(isDirty({ ...saved, interests: ['Data Science'] }, saved), true)
})

test('completeness counts only real fields and finished modules', () => {
  const empty = completeness({ profile: {}, statuses: {} })
  assert.equal(empty.percent, 0)
  const some = completeness({ profile: { university: 'SLIIT', interests: ['Data Science'] }, hasPhoto: true, statuses: { c01: 'done', c03: 'done', c02: 'in-progress' } })
  assert.equal(some.done, 5)
  assert.equal(some.percent, Math.round(5 / 13 * 100))
  assert.ok(some.missing.some(item => item.key === 'c02'))
})

test('password strength', () => {
  assert.equal(passwordStrength('short').label, 'Too short')
  assert.equal(passwordStrength('aaaaaaaaaaaaaaaa').label, 'Weak')
  assert.equal(passwordStrength('Correct-Horse-Battery-9').label, 'Strong')
})

test('module summaries use only what the modules stored', () => {
  assert.equal(personalitySummary({}), null)
  const traits = personalitySummary({ questionnaire: { traits: { OPN: 0.8, CON: 0.5, NEU: 0.2 } } })
  assert.deepEqual(traits.map(t => t.note), ['Curious, enjoys new ideas', 'Balanced', 'Calm under pressure'])
  assert.deepEqual(topSkills({ skills: [{ name: 'SQL', level: 2 }, { name: 'Python', level: 4 }, { name: 'Git', level: 4 }] }, 2).map(s => s.name), ['Git', 'Python'])
  assert.equal(roadmapProgress({ skill_gaps: { skills: [] } }), null)
  const progress = roadmapProgress({ skill_gaps: { skills: [{ status: 'met' }, { status: 'gap' }, { status: 'ok' }, { status: 'gap' }] }, roadmap: { stages: [{ steps: [{ skill_name: 'Docker' }] }] } })
  assert.equal(progress.percent, 50)
  assert.equal(progress.next.skill_name, 'Docker')
})

test('a recorded CV name is shown only for the latest assessment', () => {
  const record = { file_name: 'cv.pdf', uploaded_at: '2026-11-14T08:00:00Z' }
  assert.equal(cvName(record, '2026-11-14T08:01:00Z'), 'cv.pdf')
  assert.equal(cvName(record, '2026-11-15T08:00:00Z'), null) // a newer CV was assessed elsewhere
  assert.equal(cvName(null, '2026-11-14T08:01:00Z'), null)
})

test('photo checks', () => {
  assert.equal(photoProblem({ type: 'image/gif', size: 10 }), 'Choose a JPG or PNG photo.')
  assert.equal(photoProblem({ type: 'image/png', size: 3 * 1024 * 1024 }), 'Choose a photo of 2 MB or less.')
  assert.equal(photoProblem({ type: 'image/jpeg', size: 1000 }), '')
})
