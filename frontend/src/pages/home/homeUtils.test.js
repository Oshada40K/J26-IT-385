// Run with: node --test src/pages/home/homeUtils.test.js
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { categoryOf, fileProblem, firstName, greeting, hasSkill, previousDelta, sortCareers } from './homeUtils.js'
import { STEPS, completedCount, deriveStatuses, nextStep, personalityStatus } from './journeyStatus.js'
import { PALETTE_ITEMS, filterItems, shortcutLabel } from '../../components/shell/paletteItems.js'

test('greets by local time of day and uses the first name only', () => {
  const at = hour => greeting(new Date(2026, 10, 14, hour, 0))
  assert.equal(at(3), 'Good evening')
  assert.equal(at(9), 'Good morning')
  assert.equal(at(14), 'Good afternoon')
  assert.equal(at(20), 'Good evening')
  assert.equal(firstName('  Oshada Deneth '), 'Oshada')
  assert.equal(firstName(undefined), '')
})

test('keeps the original CV checks and messages', () => {
  const file = (name, size = 1000) => ({ name, size })
  assert.equal(fileProblem([file('cv.pdf')]), '')
  assert.equal(fileProblem([file('CV.DOCX')]), '')
  assert.equal(fileProblem([file('cv.txt')]), 'Please choose a PDF or DOCX file.')
  assert.equal(fileProblem([file('a.pdf'), file('b.pdf')]), 'Please choose one CV at a time.')
  assert.equal(fileProblem([file('cv.pdf', 0)]), 'Choose a file between 1 byte and 10 MB.')
  assert.equal(fileProblem([file('cv.pdf', 10 * 1024 * 1024 + 1)]), 'Choose a file between 1 byte and 10 MB.')
})

test('groups careers into the filter categories', () => {
  assert.equal(categoryOf('Data Engineer'), 'Data & AI')
  assert.equal(categoryOf('Cybersecurity Specialist'), 'Security')
  assert.equal(categoryOf('Product Manager'), 'Business')
  assert.equal(categoryOf('Backend Developer'), 'Engineering')
  assert.equal(categoryOf('Something New'), 'Engineering')
})

test('sorts careers without inventing growth', () => {
  const careers = [
    { career: 'A', rank: 1, new_postings: 5, growth: { pct: null } },
    { career: 'B', rank: 2, new_postings: 9, growth: { pct: -10 } },
    { career: 'C', rank: 3, new_postings: 1, growth: { pct: 25 } },
  ]
  assert.deepEqual(sortCareers(careers, 'listings').map(c => c.career), ['A', 'B', 'C'])
  assert.deepEqual(sortCareers(careers, 'new').map(c => c.career), ['B', 'A', 'C'])
  assert.deepEqual(sortCareers(careers, 'growth').map(c => c.career), ['C', 'B', 'A']) // no figure goes last
  assert.deepEqual(careers.map(c => c.career), ['A', 'B', 'C']) // input untouched
})

test('matches CV skills to market skills by name or known alias only', () => {
  const cv = ['JavaScript', 'React', 'SQL', 'HTML', 'Node', 'gcp', 'K8s']
  assert.equal(hasSkill('JavaScript', cv), true)
  assert.equal(hasSkill('HTML/CSS', cv), true)
  assert.equal(hasSkill('Node.js', cv), true)
  assert.equal(hasSkill('Google Cloud', cv), true)
  assert.equal(hasSkill('Kubernetes', cv), true)
  assert.equal(hasSkill('Java', cv), false) // JavaScript is not Java
  assert.equal(hasSkill('PostgreSQL', cv), false) // SQL is not PostgreSQL
  assert.equal(hasSkill('Python', []), false)
})

test('a delta needs two days that both have a value', () => {
  assert.equal(previousDelta([{ date: 'd1', active_listings: null }, { date: 'd2', active_listings: 100 }], 'active_listings'), null)
  const delta = previousDelta([{ date: 'd1', active_listings: 80 }, { date: 'd2', active_listings: null }, { date: 'd3', active_listings: 100 }], 'active_listings')
  assert.deepEqual({ value: delta.value, pct: delta.pct, since: delta.since.date }, { value: 20, pct: 25, since: 'd1' })
  assert.equal(previousDelta([{ x: 0 }, { x: 5 }], 'x').pct, null) // no percentage from zero
})

test('journey statuses come only from real state', () => {
  assert.equal(personalityStatus(null), 'ready')
  assert.equal(personalityStatus({ likert: {}, choices: {}, text: {} }), 'ready')
  assert.equal(personalityStatus({ likert: { q1: 3 } }), 'in-progress')
  assert.equal(personalityStatus({ questionnaire: { scored: true } }), 'in-progress')
  assert.equal(personalityStatus({ questionnaire: {}, sjt: {}, writing: {} }), 'done')
  const fresh = deriveStatuses({ cvAssessed: false, personality: 'ready', roadmapDone: false })
  assert.deepEqual(fresh, { c01: 'ready', c02: 'ready', c03: 'locked', c04: 'ready' })
  assert.equal(nextStep(fresh).key, 'c01')
  const assessed = deriveStatuses({ cvAssessed: true, personality: 'in-progress', roadmapDone: false })
  assert.deepEqual(assessed, { c01: 'done', c02: 'in-progress', c03: 'done', c04: 'ready' })
  assert.equal(nextStep(assessed).key, 'c02')
  assert.equal(completedCount(assessed), 2)
  const all = deriveStatuses({ cvAssessed: true, personality: 'done', roadmapDone: true })
  assert.equal(nextStep(all), null)
  assert.deepEqual(STEPS.map(step => step.to), ['/component01', '/component02', '/component03', '/component04'])
})

test('command palette finds modules and sections', () => {
  assert.deepEqual(filterItems(PALETTE_ITEMS, 'road').map(i => i.id), ['c04'])
  assert.deepEqual(filterItems(PALETTE_ITEMS, 'salary').map(i => i.id), ['salary'])
  assert.equal(filterItems(PALETTE_ITEMS, '').length, PALETTE_ITEMS.length)
  assert.equal(filterItems(PALETTE_ITEMS, 'zzz').length, 0)
  assert.equal(shortcutLabel('MacIntel'), '⌘K')
  assert.equal(shortcutLabel('Win32'), 'Ctrl K')
})
