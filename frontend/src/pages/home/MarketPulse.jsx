// Career Market Pulse: live job-market statistics on the Home page. Every number comes from
// /api/market/*; when the backend has no data for something, the panel says so instead of
// showing a placeholder value. One market switch scopes every section below it.
import { useEffect, useRef, useState } from 'react'
import { API_BASE_URL } from '../../api/client.js'
import { cached, hasCached, peek } from '../../api/resourceCache.js'
import Icon from '../../components/Icon.jsx'
import { ErrorState, Spinner } from '../../components/loading/index.js'
import { Bone } from '../../components/loading/Skeletons.jsx'
import { MARKETS, formatCompact, formatCount, formatDay, formatUpdated, formatWeekday, getMarketPulse } from './marketApi.js'
import { previousDelta } from './homeUtils.js'
import { useJourney } from './journey.js'
import { useReducedMotion } from './MotionRoot.jsx'
import { InfoTip, Segmented } from './ui.jsx'
import KpiTile from './KpiTile.jsx'
import TrendingCareers from './TrendingCareers.jsx'
import MarketTrendsChart from './MarketTrendsChart.jsx'
import CareerGrowth from './CareerGrowth.jsx'
import SkillDemand from './SkillDemand.jsx'
import SalaryInsights from './SalaryInsights.jsx'
import DataSources from './DataSources.jsx'
import './market.css'

const cacheKey = market => `market-pulse:${market}`

export default function MarketPulse() {
  const [market, setMarket] = useState('global')
  const [shown, setShown] = useState(() => (hasCached(cacheKey('global')) ? { market: 'global', data: peek(cacheKey('global')) } : null))
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const { cvSkills } = useJourney()
  const body = useRef(null)
  const reduced = useReducedMotion()

  useEffect(() => {
    let live = true
    const key = cacheKey(market)
    if (hasCached(key)) setShown({ market, data: peek(key) })
    setBusy(true)
    cached(key, () => getMarketPulse(API_BASE_URL, market))
      .then(data => { if (live) { setShown({ market, data }); setError('') } })
      .catch(err => { if (live) setError(err.message) })
      .finally(() => { if (live) setBusy(false) })
    return () => { live = false }
  }, [market, attempt])

  const current = shown?.market === market ? shown.data : null
  const overview = (current || shown?.data)?.overview
  const collecting = current?.overview.status === 'collecting'
  const refreshing = Boolean(current?.overview.refreshing)

  // While the backend is collecting, check back until the new snapshot is ready.
  useEffect(() => {
    if (!collecting && !refreshing) return undefined
    const timer = setTimeout(() => setAttempt(value => value + 1), collecting ? 10000 : 30000)
    return () => clearTimeout(timer)
  }, [collecting, refreshing, current])

  // Cross-fade the sections when a different market's figures arrive (opacity only).
  const lastMarket = useRef(shown?.market)
  useEffect(() => {
    if (!shown || shown.market === lastMarket.current) return
    lastMarket.current = shown.market
    if (!reduced && body.current?.animate) body.current.animate([{ opacity: 0.35 }, { opacity: 1 }], { duration: 300, easing: 'cubic-bezier(.22, 1, .36, 1)' })
  }, [shown, reduced])

  const ready = shown?.data.overview.status === 'ready'
  const data = current || shown?.data
  const counts = overview?.markets ? Object.fromEntries(overview.markets.map(entry => [entry.market, entry.active_listings])) : {}
  const label = MARKETS.find(item => item.key === market)?.label

  return <div className="market-pulse" aria-busy={busy && !current}>
    <section id="market-pulse" className="mp-hero" aria-labelledby="market-pulse-title">
      <div className="mp-hero-top">
        <div>
          <p className="mp-eyebrow"><Icon name="pulse" size={14} />CAREER MARKET PULSE</p>
          <h2 id="market-pulse-title">The job market, as it stands today.</h2>
        </div>
        <Segmented dark label="Market" value={market} onChange={setMarket} className="mp-markets"
          options={MARKETS.map(item => ({ value: item.key, label: item.label, extra: counts[item.key] != null ? formatCompact(counts[item.key]) : null }))} />
      </div>
      <Freshness overview={current?.overview} busy={busy} />
      {data && ready && <Tiles data={data} />}
      {data && ready && <p className="sr-only" aria-live="polite">{label} market: {formatCount(data.overview.totals.active_listings)} open listings from {formatCount(data.overview.totals.companies)} companies.</p>}
    </section>

    {error && !current && <ErrorState title="Market data is unavailable" message={error} onRetry={() => setAttempt(value => value + 1)} retrying={busy} />}
    {!error && !current && !shown && <PulseSkeleton />}
    {current && current.overview.status !== 'ready' && <>
      <Notice overview={current.overview} onRetry={() => setAttempt(value => value + 1)} busy={busy} />
      {current.overview.sources && <DataSources overview={current.overview} />}
    </>}
    {data && ready && (current || !error) && <div ref={body} className={`mp-body ${current ? '' : 'is-switching'}`}>
      {error && current && <p className="mp-inline-warning" role="status"><Icon name="alert" size={14} />Could not refresh just now. Showing the last loaded figures.</p>}
      <Dashboard data={data} cvSkills={cvSkills} />
    </div>}
  </div>
}

function Freshness({ overview, busy }) {
  if (!overview) return <p className="mp-fresh"><Spinner /> {busy ? 'Loading market data…' : 'Market data not loaded'}</p>
  const tone = overview.status !== 'ready' ? 'is-waiting' : overview.stale ? 'is-stale' : 'is-live'
  return <div className="mp-fresh-row">
    <p className={`mp-fresh ${tone}`}>
      <span className="live-dot" aria-hidden="true"><i /></span>
      {overview.status === 'ready' ? <>Updated {formatUpdated(overview.last_updated)}</> : overview.status === 'collecting' ? 'Collecting live listings…' : 'No data yet'}
      {overview.status === 'ready' && overview.stale && <span className="chip-warning">Older than expected</span>}
      {overview.status === 'ready' && overview.refreshing && <span className="chip-quiet"><Spinner /> Refreshing</span>}
    </p>
    <span className="mp-scope">{overview.label} market <InfoTip dark label={`About the ${overview.label} market`}>{overview.description}</InfoTip></span>
  </div>
}

function Tiles({ data }) {
  const { totals, activity } = data.overview
  const days = data.daily?.points || []
  const complete = days.filter(point => !point.partial)
  const open = days.filter(point => point.active_listings != null)
  const openDelta = previousDelta(days, 'active_listings')
  const latest = activity.latest_day
  const newDelta = latest && activity.previous_day ? { value: latest.count - activity.previous_day.count, pct: activity.previous_day.count ? Math.round(((latest.count - activity.previous_day.count) / activity.previous_day.count) * 1000) / 10 : null } : null
  return <dl className="mp-kpis">
    <KpiTile label="Open listings" value={totals.active_listings} note={`${formatCount(totals.tracked_career_listings)} in tracked tech careers`}
      delta={openDelta} deltaLabel={openDelta ? `since ${formatDay(openDelta.since.date)}` : ''}
      spark={open.length >= 2 ? open.map(point => point.active_listings) : null} sparkLabels={open.map(point => formatDay(point.date))} />
    <KpiTile label={`New postings${latest ? `, ${formatWeekday(latest.date)}` : ''}`} value={latest ? latest.count : null}
      note={activity.previous_day ? `${formatCount(activity.previous_day.count)} the day before` : 'No earlier day to compare yet'}
      delta={newDelta} deltaLabel="compared with the day before"
      spark={complete.length >= 2 ? complete.map(point => point.new_postings) : null} sparkLabels={complete.map(point => formatDay(point.date))} />
    <KpiTile label="Daily average" value={activity.daily_average == null ? null : Math.round(activity.daily_average)}
      note={activity.window_days ? `New postings over the last ${activity.window_days} full days` : 'Needs one full day of data'} />
    <KpiTile label="Companies hiring" value={totals.companies} note={`${formatCount(totals.remote_listings)} listings are remote`} />
  </dl>
}

function Notice({ overview, onRetry, busy }) {
  const collecting = overview.status === 'collecting'
  return <div className="card mp-notice" role="status">
    <span className="mp-notice-icon">{collecting ? <Spinner /> : <Icon name="alert" size={20} />}</span>
    <div>
      <strong>{collecting ? 'Collecting live job listings' : 'Market data is not available yet'}</strong>
      <p>{overview.message}{collecting && ' This page updates by itself when it is ready.'}</p>
      {!collecting && <button type="button" className="button-secondary" onClick={onRetry} disabled={busy}>Check again</button>}
    </div>
  </div>
}

export function PulseSkeleton() {
  return <div className="mp-skeleton" aria-hidden="true">
    <div className="card mp-card"><Bone w="30%" h={16} />{[96, 88, 80, 72, 64].map(w => <Bone key={w} w={`${w}%`} h={12} className="sk-gap" />)}</div>
    <div className="bento">
      <div className="card mp-card bento-wide"><Bone w="24%" h={16} /><Bone h={180} r={12} className="sk-gap" /></div>
      {[0, 1].map(i => <div key={i} className="card mp-card"><Bone w="40%" h={16} />{[90, 70, 55].map(w => <Bone key={w} w={`${w}%`} h={10} className="sk-gap" />)}</div>)}
    </div>
  </div>
}

function Dashboard({ data, cvSkills }) {
  const { overview, trending, salary, skills, daily, weekly } = data
  if (!overview.totals.active_listings) {
    return <div className="card mp-notice" role="status"><span className="mp-notice-icon"><Icon name="alert" size={20} /></span><div>
      <strong>No listings for this market right now</strong>
      <p>None of the connected job boards returned listings for the {overview.label} market in the latest collection. Nothing is shown rather than an estimate.</p>
    </div></div>
  }
  const failed = panel => panel?.error && <p className="mp-empty" role="alert"><Icon name="alert" size={16} />This panel could not be loaded: {panel.error}</p>
  return <>
    {failed(trending) || <TrendingCareers trending={trending} salary={salary.error ? null : salary} />}
    <div className="bento">
      {daily?.error && weekly?.error ? <div className="card mp-card bento-wide">{failed(daily)}</div> : <MarketTrendsChart daily={daily} weekly={weekly} />}
      {trending.error ? <div className="card mp-card">{failed(trending)}</div> : <CareerGrowth trending={trending} />}
      {skills.error ? <div id="skill-demand" className="card mp-card">{failed(skills)}</div> : <SkillDemand skills={skills} cvSkills={cvSkills} />}
    </div>
    {salary.error ? <div id="salary-insights" className="card mp-card">{failed(salary)}</div> : <SalaryInsights salary={salary} />}
    <DataSources overview={overview} />
  </>
}
