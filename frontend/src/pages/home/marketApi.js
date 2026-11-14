// Career Market Pulse API helpers and formatters for the Home page.
// Pure functions only (no React, no import.meta) so they can be tested with `node --test`.

export const MARKETS = [
  { key: 'global', label: 'Global' },
  { key: 'remote', label: 'Remote' },
  { key: 'sri_lanka', label: 'Sri Lanka' },
]

export const MARKET_ENDPOINTS = {
  overview: '/api/market/overview',
  trending: '/api/market/trending',
  salary: '/api/market/salary-insights',
  skills: '/api/market/skill-demand',
  daily: '/api/market/history',
  weekly: '/api/market/history',
}
const PARAMS = { trending: { limit: 50 }, skills: { limit: 60 }, daily: { interval: 'daily', days: 30 }, weekly: { interval: 'weekly', days: 84 } }

async function getJson(url) {
  let response
  try { response = await fetch(url) } catch { throw new Error('The CareerNova backend could not be reached.') }
  if (response.status === 404) throw new Error('This backend does not provide market data yet. Deploy the latest backend to enable Career Market Pulse.')
  if (!response.ok) {
    const detail = await response.json().then(body => body.detail).catch(() => null)
    throw new Error(typeof detail === 'string' ? detail : `Market data request failed (HTTP ${response.status}).`)
  }
  return response.json()
}

// Loads every panel for one market. The overview decides availability; a panel that fails on its
// own is returned as { error } so the rest of the dashboard still renders.
export async function getMarketPulse(baseUrl, market) {
  const load = key => getJson(`${baseUrl}${MARKET_ENDPOINTS[key]}?${new URLSearchParams({ market, ...PARAMS[key] })}`)
  const overview = await load('overview')
  if (overview.status !== 'ready') return { overview }
  const keys = Object.keys(MARKET_ENDPOINTS).filter(key => key !== 'overview')
  const panels = await Promise.all(keys.map(key => load(key).catch(error => ({ error: error.message }))))
  return { overview, ...Object.fromEntries(keys.map((key, index) => [key, panels[index]])) }
}

// ---------- formatting ----------

const integer = new Intl.NumberFormat('en-US')
export const formatCount = value => (value == null ? '—' : integer.format(value))

// 1,284 -> "1,284", 12,940 -> "12.9K", 4,200,000 -> "4.2M"
export function formatCompact(value) {
  if (value == null) return '—'
  if (Math.abs(value) < 10000) return integer.format(Math.round(value))
  const [divisor, unit] = Math.abs(value) < 1e6 ? [1e3, 'K'] : [1e6, 'M']
  return `${(value / divisor).toFixed(1).replace(/\.0$/, '')}${unit}`
}

export const formatSalary = value => (value == null ? '—' : `$${formatCompact(value)}`)

// Signed percentage with a real minus sign; null stays an em dash so "no data" never reads as 0%.
export function formatPercent(value) {
  if (value == null) return '—'
  const magnitude = Math.abs(value) >= 100 ? Math.round(Math.abs(value)) : Math.abs(value).toFixed(1)
  return `${value > 0 ? '+' : value < 0 ? '−' : ''}${magnitude}%`
}

const parseDay = day => new Date(`${day}T00:00:00Z`)
export const formatDay = day => parseDay(day).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' })
export const formatWeekday = day => parseDay(day).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' })

export function formatUpdated(iso, now = Date.now()) {
  if (!iso) return 'Not collected yet'
  const then = new Date(iso)
  const minutes = Math.round((now - then.getTime()) / 60000)
  const absolute = then.toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  if (minutes < 1) return `just now (${absolute})`
  if (minutes < 60) return `${minutes} min ago (${absolute})`
  if (minutes < 1440) return `${Math.round(minutes / 60)} h ago (${absolute})`
  return absolute
}

// Why a growth figure is missing, in words. Returns '' when growth is available.
export function growthNote(growth) {
  if (!growth || growth.ready) return ''
  if (growth.reason === 'gap') return 'Growth is paused: collection missed more than 6 days, so the two weeks cannot be compared fairly.'
  const left = growth.days_required - growth.days_collected
  return `Growth compares two full weeks of collected postings. ${growth.days_collected} of ${growth.days_required} days collected, ${left} to go.`
}

// Clean axis ticks: 0 and up to `count` round steps that cover `max`.
export function niceTicks(max, count = 4) {
  if (!(max > 0)) return [0, 1]
  const rough = max / count
  const power = 10 ** Math.floor(Math.log10(rough))
  const step = Math.max(1, [1, 2, 2.5, 5, 10].map(m => m * power).find(s => s >= rough))
  const ticks = []
  for (let tick = 0; tick < max + step; tick += step) ticks.push(Math.round(tick))
  return ticks
}
