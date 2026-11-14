// Run with: node --test src/pages/home/marketApi.test.js
import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import {
  MARKET_ENDPOINTS, formatCompact, formatCount, formatPercent, formatSalary, formatUpdated, getMarketPulse, growthNote, niceTicks,
} from './marketApi.js'

const originalFetch = globalThis.fetch
afterEach(() => { globalThis.fetch = originalFetch })
const baseUrl = 'http://market.test'

test('loads every panel for the chosen market once the overview is ready', async () => {
  const urls = []
  globalThis.fetch = async url => { urls.push(url); return Response.json({ status: 'ready', path: new URL(url).pathname }) }
  const data = await getMarketPulse(baseUrl, 'sri_lanka')
  assert.deepEqual(Object.keys(data), ['overview', 'trending', 'salary', 'skills', 'daily', 'weekly'])
  assert.equal(urls.length, 6)
  for (const url of urls) assert.equal(new URL(url).searchParams.get('market'), 'sri_lanka')
  assert.equal(urls[0], `${baseUrl}${MARKET_ENDPOINTS.overview}?market=sri_lanka`)
  assert.ok(urls.includes(`${baseUrl}/api/market/history?market=sri_lanka&interval=weekly&days=84`))
  assert.ok(urls.includes(`${baseUrl}/api/market/trending?market=sri_lanka&limit=50`))
})

test('does not request panels while the backend has no snapshot', async () => {
  let calls = 0
  globalThis.fetch = async () => { calls += 1; return Response.json({ status: 'collecting', message: 'The first collection is running.' }) }
  const data = await getMarketPulse(baseUrl, 'global')
  assert.deepEqual(Object.keys(data), ['overview'])
  assert.equal(calls, 1)
})

test('one failing panel does not hide the others', async () => {
  globalThis.fetch = async url => (url.includes('salary-insights')
    ? Response.json({ detail: 'Market data storage is unavailable.' }, { status: 503 })
    : Response.json({ status: 'ready' }))
  const data = await getMarketPulse(baseUrl, 'global')
  assert.deepEqual(data.salary, { error: 'Market data storage is unavailable.' })
  assert.equal(data.trending.status, 'ready')
})

test('explains an older backend and an unreachable backend', async () => {
  globalThis.fetch = async () => new Response('Not Found', { status: 404 })
  await assert.rejects(getMarketPulse(baseUrl, 'global'), /does not provide market data yet/)
  globalThis.fetch = async () => { throw new TypeError('fetch failed') }
  await assert.rejects(getMarketPulse(baseUrl, 'global'), /could not be reached/)
  globalThis.fetch = async () => new Response('<html>Bad gateway</html>', { status: 502 })
  await assert.rejects(getMarketPulse(baseUrl, 'global'), /HTTP 502/)
})

test('formats numbers without inventing values for missing data', () => {
  assert.equal(formatCount(5217), '5,217')
  assert.equal(formatCount(null), '—')
  assert.equal(formatCompact(9999), '9,999')
  assert.equal(formatCompact(12940), '12.9K')
  assert.equal(formatCompact(4200000), '4.2M')
  assert.equal(formatSalary(87500), '$87.5K')
  assert.equal(formatSalary(undefined), '—')
  assert.equal(formatPercent(12.44), '+12.4%')
  assert.equal(formatPercent(-100), '−100%')
  assert.equal(formatPercent(0), '0.0%')
  assert.equal(formatPercent(null), '—')
})

test('describes why growth is missing', () => {
  assert.equal(growthNote({ ready: true }), '')
  assert.match(growthNote({ ready: false, reason: 'collecting', days_collected: 3, days_required: 14 }), /3 of 14 days collected, 11 to go/)
  assert.match(growthNote({ ready: false, reason: 'gap', days_collected: 14, days_required: 14 }), /paused/)
})

test('axis ticks are round and cover the maximum', () => {
  assert.deepEqual(niceTicks(1061), [0, 500, 1000, 1500])
  assert.deepEqual(niceTicks(91), [0, 25, 50, 75, 100])
  assert.deepEqual(niceTicks(3), [0, 1, 2, 3])
  assert.deepEqual(niceTicks(0), [0, 1])
})

test('shows relative and absolute update times', () => {
  const now = Date.parse('2026-11-14T02:00:00Z')
  assert.equal(formatUpdated(null), 'Not collected yet')
  assert.match(formatUpdated('2026-11-14T01:50:00Z', now), /^10 min ago \(/)
  assert.match(formatUpdated('2026-11-13T20:00:00Z', now), /^6 h ago \(/)
  assert.doesNotMatch(formatUpdated('2026-11-10T20:00:00Z', now), /ago/)
})
