import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { ENDPOINTS, getAllCareerResults, uploadAndPredictCV } from './careerApi.js'

const originalFetch = globalThis.fetch
afterEach(() => { globalThis.fetch = originalFetch })
const session = { candidate_id: 'candidate_test', access_token: 'test-token' }
const baseUrl = 'http://career.test'
const completed = { candidate_id: session.candidate_id, assessment_id: 'assessment_new', status: 'completed' }
const response = () => Response.json({ candidate_id: session.candidate_id })

test('waits for completed upload before calling all three authenticated career APIs', async () => {
  let finishUpload
  const pending = new Promise(resolve => { finishUpload = resolve })
  const calls = []
  globalThis.fetch = async (url, options) => { calls.push({ url, options }); return response() }
  let assessed = false
  const prediction = uploadAndPredictCV('cv-file', {
    uploadCV: file => { assert.equal(file, 'cv-file'); return pending },
    savedSession: () => session, baseUrl, onAssessed: () => { assessed = true },
  })
  assert.equal(calls.length, 0)
  assert.equal(assessed, false)
  finishUpload(completed)
  const result = await prediction
  assert.equal(assessed, true)
  assert.equal(result.assessmentId, completed.assessment_id)
  assert.equal(result.candidateId, session.candidate_id)
  assert.deepEqual(calls.map(call => call.url), Object.values(ENDPOINTS).map(path => `${baseUrl}${path}?candidate_id=candidate_test`))
  for (const call of calls) assert.equal(call.options.headers.Authorization, 'Bearer test-token')
  for (const value of Object.values(result.careerResults)) assert.equal(value.error, null)
})

test('failed upload never starts career prediction', async () => {
  globalThis.fetch = () => { assert.fail('Career API must not run') }
  await assert.rejects(uploadAndPredictCV('cv', {
    uploadCV: async () => { throw new Error('Invalid CV') }, savedSession: () => session, baseUrl,
  }), /Invalid CV/)
})

test('incomplete assessment or mismatched session never starts prediction', async () => {
  globalThis.fetch = () => { assert.fail('Career API must not run') }
  for (const assessment of [{ ...completed, status: 'pending' }, { ...completed, candidate_id: 'other' }]) {
    await assert.rejects(uploadAndPredictCV('cv', {
      uploadCV: async () => assessment, savedSession: () => session, baseUrl,
    }), /completed CV assessment and matching candidate session/)
  }
})

test('all endpoints run even when one fails, preserving successful results', async () => {
  const calls = []
  globalThis.fetch = async url => {
    calls.push(url)
    if (url.includes('/best-job')) return Response.json({ detail: 'Missing personality profile' }, { status: 502 })
    return response()
  }
  const results = await getAllCareerResults(baseUrl, session)
  assert.equal(calls.length, 3)
  assert.equal(results.bestJob.error, 'HTTP 502: Missing personality profile')
  assert.equal(results.bestJob.data, null)
  assert.equal(results.topJobs.data.candidate_id, session.candidate_id)
  assert.equal(results.explanation.error, null)
})

test('candidate mismatches cannot be displayed as successful predictions', async () => {
  globalThis.fetch = async () => Response.json({ candidate_id: 'another-candidate' })
  const results = await getAllCareerResults(baseUrl, session)
  for (const value of Object.values(results)) {
    assert.equal(value.data, null)
    assert.match(value.error, /another candidate/)
  }
})

test('old deployed backend returning a sample gives a deployment error, not a retry loop', async () => {
  globalThis.fetch = async () => Response.json({ candidate_id: 'sample_candidate_001', best_job: 'Sample job' })
  const results = await getAllCareerResults(baseUrl, session)
  for (const value of Object.values(results)) {
    assert.equal(value.data, null)
    assert.match(value.error, /Deploy the updated Component 3 backend with candidate_id support/)
    assert.match(value.error, /http:\/\/career.test/)
  }
})

test('network failures settle all result states without leaving loading flags', async () => {
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch') }
  const results = await getAllCareerResults(baseUrl, session)
  for (const value of Object.values(results)) {
    assert.equal(value.loading, false)
    assert.equal(value.error, `Unable to connect to backend at ${baseUrl}.`)
  }
})
