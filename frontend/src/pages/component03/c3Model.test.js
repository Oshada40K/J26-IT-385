import test from 'node:test'
import assert from 'node:assert/strict'
import { confidenceShares, gainsByTechnology, gapToTop, isNarrow, isTechnicalFactor, rangeLabel, reasonMatches, zoomAxis } from './c3Model.js'

const REASONS = [
  'The main reason for this match: how many of your technical skills this job actually uses.',
  'Your soft skills also fit what this job needs, especially Speaking, Writing and Critical Thinking.',
  "What lowered your score: you cover only some of this job's tool categories and less evidence of Reading Comprehension than this job expects.",
]

test('a range that rounds to one number reads as stable', () => {
  assert.equal(rangeLabel(42.32, 42.35), 'Stable at ~42')
  assert.equal(rangeLabel(40.2, 44.9), '40–45')
  assert.equal(isNarrow(42.32, 42.35), true)
  assert.equal(isNarrow(40, 44), false)
})

test('factors link to the reasons that mention them', () => {
  assert.deepEqual(reasonMatches('Technical skills used in this job', REASONS), [0])
  assert.deepEqual(reasonMatches('Speaking', REASONS), [1])
  assert.deepEqual(reasonMatches('Tool category coverage', REASONS), [2])
  assert.deepEqual(reasonMatches('Reading Comprehension', REASONS), [2])
  assert.deepEqual(reasonMatches('Monitoring', REASONS), [])
  assert.equal(isTechnicalFactor('Technical skills used in this job'), true)
  assert.equal(isTechnicalFactor('Speaking'), false)
})

test('gap to the top score uses the reported precision', () => {
  assert.deepEqual(gapToTop(42.33, 42.33), { gap: 0, tied: true, label: 'Tied for #1' })
  assert.equal(gapToTop(42.29, 42.33).label, '−0.04 pts')
})

test('zoomed axis spans the scores with padding', () => {
  const axis = zoomAxis([42.0, 42.33])
  assert.ok(axis.lo < 42 && axis.hi > 42.33)
  assert.ok(axis.position(42.33) > axis.position(42.0))
})

test('confidence shares and what-if gains', () => {
  assert.deepEqual(confidenceShares({ high: 2, medium: 1, low: 1 }).map(s => s.share), [0.5, 0.25, 0.25])
  assert.deepEqual(confidenceShares({}), [])
  const gains = gainsByTechnology([{ action: 'learn', technology: 'Jenkins CI', score_gain: 1.16 }, { action: 'improve', technology: 'Python', score_gain: 0.4 }, { action: 'learn', technology: 'C#', score_gain: 0 }])
  assert.deepEqual(Object.keys(gains), ['Jenkins CI'])
})
