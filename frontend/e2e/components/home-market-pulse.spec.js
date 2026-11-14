// Home page: Career Market Pulse section (not a research component; it lives under the CV upload).
// The e2e backend never contacts job boards (MARKET_AUTO_REFRESH=false), so the dashboard states
// are driven by canned /api/market responses. The numbers below are test fixtures only.
import { expect, test } from '@playwright/test'

const CAREERS = ['Software Engineer', 'Product Manager', 'Machine Learning / AI Engineer', 'DevOps / Site Reliability Engineer',
  'ERP / CRM Consultant', 'Cybersecurity Specialist', 'Backend Developer', 'Data Engineer', 'Systems / Network Administrator',
  'Full Stack Developer', 'Data Analyst', 'QA / Test Engineer']
const day = offset => new Date(Date.UTC(2026, 2, 16 + offset)).toISOString().slice(0, 10)
const SIZE = { global: 5217, remote: 832, sri_lanka: 407 }

function envelope(market, extra = {}) {
  return { market, label: { global: 'Global', remote: 'Remote', sri_lanka: 'Sri Lanka' }[market], description: `Fixture description for ${market}.`,
    status: 'ready', message: null, snapshot_date: day(0), collection_started: day(-14), last_updated: new Date().toISOString(),
    refreshing: false, stale: false, ...extra }
}

function payload(name, market, params, { growthReady = true } = {}) {
  const growth = growthReady ? { ready: true, days_collected: 14, days_required: 14, reason: null, method: 'Latest 7 days compared with the previous 7 days.' }
    : { ready: false, days_collected: 3, days_required: 14, reason: 'collecting', method: 'Latest 7 days compared with the previous 7 days.' }
  if (name === 'overview') {
    return { ...envelope(market), totals: { active_listings: SIZE[market], companies: 1871, tracked_career_listings: 1678, remote_listings: 832, listings_with_salary: 44 },
      activity: { latest_day: { date: day(-1), count: 780 }, previous_day: { date: day(-2), count: 804 }, new_postings: 5005, window_days: 7, daily_average: 715, new_today_so_far: 5 },
      markets: Object.entries(SIZE).map(([key, active]) => ({ market: key, label: key, active_listings: active })), growth,
      sources: [{ source: 'arbeitnow', label: 'Arbeitnow', url: 'https://www.arbeitnow.com', coverage: 'Full public feed.', ok: true, partial: false, fetched: 5203, configured: true, error: null },
        { source: 'himalayas', label: 'Himalayas', url: 'https://himalayas.app', coverage: 'Sri Lanka filter.', ok: true, partial: true, fetched: 400, configured: true, error: 'HTTPStatusError: 429' },
        { source: 'jobicy', label: 'Jobicy', url: 'https://jobicy.com', coverage: 'Remote roles, last 7 days.', ok: false, partial: false, fetched: 0, configured: true, error: 'HTTPStatusError: 503' }],
      collection: { status: 'partial', unique_listings: 5217, duplicates_removed: 499 }, storage: 'sqlite', refresh_interval_hours: 12 }
  }
  if (name === 'trending') {
    const pcts = [50, -25, 12.5, 0, null, 8, -4.2, 30, 2, -60, 5, 1]
    return { ...envelope(market), growth, tracked_careers: CAREERS.length, window_days: 7,
      careers: CAREERS.map((career, index) => ({ rank: index + 1, career, active_listings: 280 - index * 20, share_pct: 16.3 - index, new_postings: 200 - index * 10,
        growth: !growthReady ? { pct: null, direction: null, reason: 'collecting' }
          : pcts[index] == null ? { pct: null, direction: null, reason: 'low_volume', current_avg: 0.3, previous_avg: 0.1 }
            : { pct: pcts[index], direction: pcts[index] > 0 ? 'up' : pcts[index] < 0 ? 'down' : 'flat', reason: null, current_avg: 3, previous_avg: 2 },
        trend: Array.from({ length: 14 }, (_, i) => ({ date: day(i - 14), new_postings: 10 + ((index + i) % 5) })) })) }
  }
  if (name === 'salary-insights') {
    return { ...envelope(market), currency: 'USD', basis: 'Annual pay in USD as disclosed.', min_sample: 5, listings_with_salary: 44, active_listings: SIZE[market],
      overall: { median: 87500, p25: 46500, p75: 141820, sample_size: 44 },
      careers: market === 'sri_lanka' ? [] : [{ career: 'Software Engineer', median: 130000, p25: 110000, p75: 150000, sample_size: 9 }, { career: 'Data Analyst', median: 82000, p25: 70000, p75: 95000, sample_size: 6 }],
      insufficient: [{ career: 'Engineering Manager', sample_size: 3 }] }
  }
  if (name === 'skill-demand') {
    return { ...envelope(market), listings_with_skills: 2570, active_listings: SIZE[market],
      skills: ['Python', 'SQL', 'AWS', 'Java', 'React', 'Machine Learning'].map((skill, index) => ({ rank: index + 1, skill, listings: 800 - index * 90, share_pct: 31.2 - index * 3 })) }
  }
  if (params.get('interval') === 'weekly') {
    return { ...envelope(market), interval: 'weekly', career: null, series_start: day(-20), points: [
      { week_start: day(-21), new_postings: 4100, days: 6, partial: true, backfilled: true },
      { week_start: day(-14), new_postings: 4700, days: 7, partial: false, backfilled: false },
      { week_start: day(-7), new_postings: 5005, days: 7, partial: false, backfilled: false },
      { week_start: day(0), new_postings: 5, days: 1, partial: true, backfilled: false }] }
  }
  return { ...envelope(market), interval: 'daily', career: null, series_start: day(-20),
    points: Array.from({ length: 21 }, (_, i) => ({ date: day(i - 20), new_postings: i === 20 ? 5 : 600 + ((i * 97) % 400), active_listings: i < 6 ? null : 5000 + i * 10, backfilled: i < 6, partial: i === 20 })) }
}

async function mockMarket(page, options = {}) {
  const requested = []
  await page.route('**/api/market/**', route => {
    const url = new URL(route.request().url())
    requested.push(`${url.pathname}?market=${url.searchParams.get('market')}`)
    const name = url.pathname.split('/').pop()
    if (options.respond) return options.respond(route, name)
    return route.fulfill({ json: payload(name, url.searchParams.get('market'), url.searchParams, options) })
  })
  return requested
}

const pulse = page => page.getByRole('region', { name: 'The job market, as it stands today.' })
const card = (page, title) => pulse(page).locator('.mp-card').filter({ has: page.getByRole('heading', { name: title, exact: true }) })

test.describe('Home - Career Market Pulse', () => {
  test('sits under the CV upload and shows every market panel', async ({ page }) => {
    await mockMarket(page)
    await page.goto('/')
    await expect(pulse(page)).toBeVisible()
    // The CV upload is unchanged and stays above the new section.
    const upload = await page.locator('.cv-panel').boundingBox()
    const section = await pulse(page).boundingBox()
    expect(section.y).toBeGreaterThan(upload.y + upload.height)
    await expect(page.getByLabel('Choose your CV')).toBeAttached()

    await expect(pulse(page).locator('.mp-tile').first()).toContainText('5,217')
    await expect(pulse(page).getByText(/^Updated /)).toBeVisible()
    const rows = card(page, 'Trending careers').locator('tbody tr')
    await expect(rows).toHaveCount(10)
    await expect(rows.first()).toContainText('01')
    await expect(rows.first()).toContainText('Software Engineer')
    await expect(rows.first().locator('.mp-delta.is-up')).toHaveText(/Up\s*\+50\.0%/)
    await expect(rows.nth(1).locator('.mp-delta.is-down')).toHaveText(/Down\s*−25\.0%/)
    await expect(rows.nth(4).locator('.mp-delta.is-none')).toBeVisible()   // too few postings: no percentage

    const growth = card(page, 'Career growth')
    await expect(growth.getByRole('heading', { name: 'Rising' })).toBeVisible()
    await expect(growth.locator('.mp-movers').first().locator('li').first()).toContainText('Software Engineer')
    await expect(growth.locator('.mp-movers').nth(1).locator('li').first()).toContainText('Full Stack Developer')   // -60% is the steepest fall
    await expect(card(page, 'Skill demand').locator('li').first()).toContainText('Python')
    await expect(card(page, 'Salary insights').locator('tbody tr').first()).toContainText('$130K')
    await expect(card(page, 'Market trends').locator('svg[role=img]')).toBeVisible()

    const sources = pulse(page).locator('.mp-sources')
    await expect(sources.getByRole('link', { name: 'Arbeitnow' })).toHaveAttribute('href', 'https://www.arbeitnow.com')
    await expect(sources.locator('li').filter({ hasText: 'Jobicy' })).toContainText('Failed')
    await expect(sources.getByRole('link', { name: 'Jobicy' })).toHaveAttribute('href', 'https://jobicy.com')
    await expect(sources.locator('li').filter({ hasText: 'Himalayas' })).toContainText('Partial')
    await expect(page.locator('#main-navigation a')).toHaveCount(6)   // no new sidebar item
  })

  test('keeps the three markets separate', async ({ page }) => {
    const requested = await mockMarket(page)
    await page.goto('/')
    await expect(pulse(page).locator('.mp-tile').first()).toContainText('5,217')
    await pulse(page).getByRole('button', { name: /^Sri Lanka/ }).click()
    await expect(pulse(page).locator('.mp-tile').first()).toContainText('407')
    await expect(pulse(page).getByText('Fixture description for sri_lanka.')).toBeVisible()
    await expect(card(page, 'Salary insights')).toContainText('A median by career is not available yet')
    expect(requested.filter(url => url.endsWith('market=sri_lanka')).length).toBeGreaterThanOrEqual(6)
    await pulse(page).getByRole('button', { name: /^Remote/ }).click()
    await expect(pulse(page).locator('.mp-tile').first()).toContainText('832')
  })

  test('switches between daily and weekly history and offers a table', async ({ page }) => {
    await mockMarket(page)
    await page.goto('/')
    const trends = card(page, 'Market trends')
    await expect(trends.locator('.mp-legend').getByText('From posting dates, before collection began')).toBeVisible()
    await trends.locator('svg[role=img]').hover()
    await expect(trends.locator('.mp-tooltip')).toContainText('new postings')
    await trends.getByRole('button', { name: 'Weekly' }).click()
    await expect(trends.locator('.mp-chart-bar')).toHaveCount(4)
    await expect(trends.getByText('Partial week', { exact: true })).toBeVisible()
    await trends.getByText('Show these figures as a table').click()
    await expect(trends.locator('details tbody tr')).toHaveCount(4)
    await expect(trends.locator('details tbody tr').nth(2)).toContainText('5,005')
  })

  test('shows no growth percentage before two weeks are collected', async ({ page }) => {
    await mockMarket(page, { growthReady: false })
    await page.goto('/')
    const growth = card(page, 'Career growth')
    await expect(growth).toContainText('Growth percentages are not available yet')
    await expect(growth).toContainText('3 of 14 days collected, 11 to go')
    await expect(growth.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '3')
    await expect(pulse(page).locator('.mp-delta.is-up, .mp-delta.is-down')).toHaveCount(0)
    await expect(card(page, 'Trending careers').locator('tbody tr')).toHaveCount(10)
  })

  test('reports an older backend instead of showing numbers', async ({ page }) => {
    await mockMarket(page, { respond: route => route.fulfill({ status: 404, json: { detail: 'Not Found' } }) })
    await page.goto('/')
    await expect(pulse(page).getByText('Market data is unavailable')).toBeVisible()
    await expect(pulse(page).getByRole('alert')).toContainText('does not provide market data yet')
    await expect(pulse(page).locator('.mp-tile')).toHaveCount(0)
    await expect(page.getByLabel('Choose your CV')).toBeAttached()   // the rest of Home still works
  })

  test('real backend with nothing collected says so', async ({ page }) => {
    await page.goto('/')
    await expect(pulse(page).getByText('Market data is not available yet')).toBeVisible()
    await expect(pulse(page).getByText('No market data has been collected yet.')).toBeVisible()
    await expect(pulse(page).locator('.mp-tile')).toHaveCount(0)
  })
})
