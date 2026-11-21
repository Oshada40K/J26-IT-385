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

// The market sections load when they come near the viewport, and figures count up once seen.
async function openPulse(page) {
  await page.goto('/')
  await page.locator('#market-area').scrollIntoViewIfNeeded()
  await expect(page.locator('#market-pulse')).toBeVisible()
}
const section = (page, id) => page.locator(`#${id}`)
const titled = (page, title) => page.locator('.market-pulse section').filter({ has: page.getByRole('heading', { name: title, exact: true }) })

test.describe('Home - Career Market Pulse', () => {
  test('sits under the CV upload and shows every market panel', async ({ page }) => {
    await mockMarket(page)
    await openPulse(page)
    // The CV upload is unchanged and stays above the new section.
    const upload = await page.locator('#cv-upload').boundingBox()
    const area = await page.locator('#market-area').boundingBox()
    expect(area.y).toBeGreaterThan(upload.y + upload.height)
    await expect(page.getByLabel('Choose your CV')).toBeAttached()

    await expect(page.locator('.mp-kpis .kpi').first()).toContainText('5,217')
    await expect(page.getByText(/^Updated /)).toBeVisible()
    const trending = section(page, 'trending-careers')
    await trending.scrollIntoViewIfNeeded()
    const rows = trending.locator('.trend-row')
    await expect(rows).toHaveCount(10)
    await expect(rows.first()).toContainText('01')
    await expect(rows.first()).toContainText('Software Engineer')
    await expect(rows.first().locator('.delta.is-up')).toHaveText(/Up\s*\+50\.0%/)
    await expect(rows.nth(1).locator('.delta.is-down')).toHaveText(/Down\s*−25\.0%/)
    await expect(rows.nth(4)).toContainText('Too few postings') // no percentage from a tiny base

    const growth = titled(page, 'Career growth')
    await growth.scrollIntoViewIfNeeded()
    await expect(growth.locator('.diverging li').first()).toContainText('Software Engineer')
    await expect(growth.locator('.diverging li').last()).toContainText('Full Stack Developer') // -60% is the steepest fall
    await expect(section(page, 'skill-demand').locator('.skill-bars li').first()).toContainText('Python')
    const salary = section(page, 'salary-insights')
    await salary.scrollIntoViewIfNeeded()
    await expect(salary.locator('tbody tr').first()).toContainText('$130K')
    await expect(titled(page, 'Market trends').locator('svg[role=img]')).toBeVisible()

    const sources = section(page, 'data-sources')
    await sources.scrollIntoViewIfNeeded()
    await expect(sources.getByRole('link', { name: 'Arbeitnow' })).toHaveAttribute('href', 'https://www.arbeitnow.com')
    await expect(sources.locator('li').filter({ hasText: 'Himalayas' })).toContainText('Partial')
    await expect(sources.locator('li').filter({ hasText: 'Jobicy' })).toContainText('Failed')
    await expect(page.locator('#main-navigation a')).toHaveCount(6) // no new sidebar item
  })

  test('keeps the three markets separate', async ({ page }) => {
    const requested = await mockMarket(page)
    await openPulse(page)
    const firstTile = page.locator('.mp-kpis .kpi').first()
    await expect(firstTile).toContainText('5,217')
    await page.locator('.mp-markets').getByRole('button', { name: /^Sri Lanka/ }).click()
    await expect(firstTile).toContainText('407')
    await expect(page.getByRole('tooltip').filter({ hasText: 'Fixture description for sri_lanka.' })).toBeAttached()
    await expect(section(page, 'salary-insights')).toContainText('A median by career is not available yet')
    expect(requested.filter(url => url.endsWith('market=sri_lanka')).length).toBeGreaterThanOrEqual(6)
    await page.locator('.mp-markets').getByRole('button', { name: /^Remote/ }).click()
    await expect(firstTile).toContainText('832')
  })

  test('filters, sorts, expands and shows details for careers', async ({ page }) => {
    await mockMarket(page)
    await openPulse(page)
    const trending = section(page, 'trending-careers')
    await trending.scrollIntoViewIfNeeded()
    await trending.getByRole('button', { name: /^Data & AI/ }).click()
    await expect(trending.locator('.trend-row .career-name')).toHaveText(['Machine Learning / AI Engineer', 'Data Engineer', 'Data Analyst'])
    await trending.getByRole('button', { name: /^All/ }).click()
    await trending.getByRole('button', { name: 'Show all 12 careers' }).click()
    await expect(trending.locator('.trend-row')).toHaveCount(12)
    await trending.getByRole('button', { name: 'Growth' }).click()
    await expect(trending.locator('.trend-row .career-name').first()).toHaveText('Software Engineer') // +50% is the largest rise
    const view = trending.getByRole('button', { name: /^(View|Hide) Software Engineer$/ })
    await view.click()
    await expect(view).toHaveAttribute('aria-expanded', 'true')
    await expect(trending.locator('.career-detail')).toContainText('Median disclosed salary $130K')
  })

  test('switches between daily and weekly history and offers a table', async ({ page }) => {
    await mockMarket(page)
    await openPulse(page)
    const trends = titled(page, 'Market trends')
    await trends.scrollIntoViewIfNeeded()
    await expect(trends.locator('.chart-legend').getByText('From posting dates, before collection began')).toBeVisible()
    await trends.locator('svg[role=img]').hover()
    await expect(trends.locator('.chart-tooltip')).toContainText('new postings')
    await trends.getByRole('button', { name: 'Weekly' }).click()
    await expect(trends.locator('.chart-bar')).toHaveCount(4)
    await expect(trends.locator('.chart-legend').getByText('Partial week', { exact: true })).toBeVisible()
    await trends.getByRole('button', { name: 'Show these figures as a table' }).click()
    await expect(trends.locator('.disclosure-body tbody tr')).toHaveCount(4)
    await expect(trends.locator('.disclosure-body tbody tr').nth(2)).toContainText('5,005')
  })

  test('shows no growth percentage before two weeks are collected', async ({ page }) => {
    await mockMarket(page, { growthReady: false })
    await openPulse(page)
    const growth = titled(page, 'Career growth')
    await growth.scrollIntoViewIfNeeded()
    await expect(growth).toContainText('Growth percentages are not available yet')
    await expect(growth).toContainText('3 of 14 days collected, 11 to go')
    await expect(growth.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '3')
    await expect(page.locator('.market-pulse .delta.is-up, .market-pulse .delta.is-down')).toHaveCount(0)
    await expect(section(page, 'trending-careers').locator('.trend-row')).toHaveCount(10)
    await expect(section(page, 'trending-careers').getByRole('button', { name: 'Growth' })).toBeDisabled()
  })

  test('reports an older backend instead of showing numbers', async ({ page }) => {
    await mockMarket(page, { respond: route => route.fulfill({ status: 404, json: { detail: 'Not Found' } }) })
    await openPulse(page).catch(() => {}) // the band itself still renders its heading
    await page.locator('#market-area').scrollIntoViewIfNeeded()
    await expect(page.getByText('Market data is unavailable')).toBeVisible()
    await expect(page.locator('.market-pulse').getByRole('alert')).toContainText('does not provide market data yet')
    await expect(page.locator('.mp-kpis .kpi')).toHaveCount(0)
    await expect(page.getByLabel('Choose your CV')).toBeAttached() // the rest of Home still works
  })

  test('real backend with nothing collected says so', async ({ page }) => {
    await openPulse(page)
    await expect(page.getByText('Market data is not available yet')).toBeVisible()
    await expect(page.getByText('No market data has been collected yet.')).toBeVisible()
    await expect(page.locator('.mp-kpis .kpi')).toHaveCount(0)
  })
})

test.describe('Home - redesign', () => {
  test('keeps the headline, greets the student and shows the real journey', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1, name: 'Big possibilities. Start with your CV.' })).toBeVisible()
    await expect(page.locator('.hero-greeting')).toHaveText(/^Good (morning|afternoon|evening), Component/)
    const journey = page.locator('.journey')
    await expect(journey.getByRole('link')).toHaveCount(4)
    await expect(journey).not.toContainText('Checking')
    // The shared test account has not finished every step, so the journey cannot read 4 of 4.
    await expect(journey.locator('.journey-count')).toHaveText(/^[0-3] of 4 complete$/)
    await journey.getByRole('link', { name: /Learning roadmap/ }).click()
    await expect(page).toHaveURL('/component04')
  })

  test('command palette opens with Ctrl+K and jumps to a module', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('button', { name: 'Search modules and sections' })).toBeVisible() // the shortcut listens once the app shell is up
    await page.keyboard.press('Control+K')
    const dialog = page.getByRole('dialog', { name: 'Search CareerNova' })
    await expect(dialog).toBeVisible()
    await page.keyboard.type('road')
    await expect(dialog.getByRole('option')).toHaveCount(1)
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL('/component04')
    await expect(dialog).toHaveCount(0)
  })

  test('dark mode applies to every page and is remembered', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Switch to dark mode' }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    await expect(page.locator('.cn-home')).toHaveAttribute('data-theme', 'dark')
    await page.reload()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    await page.goto('/component01')
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    await page.getByRole('button', { name: 'Switch to light mode' }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  })

  test('the upload card keeps its keyboard path and messages', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('button', { name: 'Analyze my CV' })).toHaveCount(0)
    await page.getByLabel('Choose your CV').setInputFiles({ name: 'big.pdf', mimeType: 'application/pdf', buffer: Buffer.alloc(0) })
    await expect(page.getByRole('alert')).toHaveText('Choose a file between 1 byte and 10 MB.')
    await page.getByLabel('Choose your CV').setInputFiles({ name: 'cv.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.4') })
    await expect(page.getByRole('alert')).toHaveCount(0)
    await expect(page.getByText('cv.pdf')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Analyze my CV' })).toBeEnabled()
  })
})
