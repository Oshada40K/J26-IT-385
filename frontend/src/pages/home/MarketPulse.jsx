// Career Market Pulse: live job-market statistics shown on the Home page under the CV upload.
// Every number comes from /api/market/*; when the backend has no data for something, the panel
// says so instead of showing a placeholder value.
import { useEffect, useRef, useState } from 'react'
import { API_BASE_URL } from '../../api/client.js'
import { cached, hasCached, peek } from '../../api/resourceCache.js'
import Icon from '../../components/Icon.jsx'
import { ErrorState, Spinner } from '../../components/loading/index.js'
import { Bone } from '../../components/loading/Skeletons.jsx'
import {
  MARKETS, formatCompact, formatCount, formatDay, formatPercent, formatSalary, formatUpdated, formatWeekday,
  getMarketPulse, growthNote, niceTicks,
} from './marketApi.js'
import './MarketPulse.css'

const cacheKey = market => `market-pulse:${market}`

export default function MarketPulse() {
  const [market, setMarket] = useState('global')
  const [shown, setShown] = useState(() => (hasCached(cacheKey('global')) ? { market: 'global', data: peek(cacheKey('global')) } : null))
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [attempt, setAttempt] = useState(0)

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

  const ready = shown?.data.overview.status === 'ready'
  return <section className="market-pulse" aria-labelledby="market-pulse-title" aria-busy={busy && !current}>
    <div className="mp-band">
      <div className="mp-band-top">
        <div>
          <p className="mp-eyebrow"><Icon name="pulse" size={14} />CAREER MARKET PULSE</p>
          <h2 id="market-pulse-title">The job market, as it stands today.</h2>
        </div>
        <div className="mp-tabs" role="group" aria-label="Market">
          {MARKETS.map(item => <button key={item.key} type="button" className={item.key === market ? 'is-active' : ''} aria-pressed={item.key === market} onClick={() => setMarket(item.key)}>
            {item.label}
            {overview?.markets && <small>{formatCompact(overview.markets.find(entry => entry.market === item.key)?.active_listings)}</small>}
          </button>)}
        </div>
      </div>
      <Freshness overview={current?.overview} busy={busy} />
      {current && ready && <Tiles overview={current.overview} />}
    </div>

    {error && !current && <ErrorState title="Market data is unavailable" message={error} onRetry={() => setAttempt(value => value + 1)} retrying={busy} />}
    {!error && !current && !shown && <PulseSkeleton />}
    {current && current.overview.status !== 'ready' && <Notice overview={current.overview} onRetry={() => setAttempt(value => value + 1)} busy={busy} />}
    {(current || (shown && !error)) && ready && <div className={`mp-body ${current ? '' : 'is-switching'}`}>
      {error && current && <p className="mp-inline-warning" role="status"><Icon name="alert" size={14} />Could not refresh just now. Showing the last loaded figures.</p>}
      <Dashboard data={current || shown.data} />
    </div>}
    {overview?.sources && <Sources overview={overview} />}
  </section>
}

function Freshness({ overview, busy }) {
  if (!overview) return <p className="mp-fresh"><Spinner /> {busy ? 'Loading market data…' : 'Market data not loaded'}</p>
  const tone = overview.status !== 'ready' ? 'is-waiting' : overview.stale ? 'is-stale' : 'is-live'
  return <div className="mp-fresh-row">
    <p className={`mp-fresh ${tone}`}>
      <i aria-hidden="true" />
      {overview.status === 'ready' ? <>Updated {formatUpdated(overview.last_updated)}</> : overview.status === 'collecting' ? 'Collecting live listings…' : 'No data yet'}
      {overview.status === 'ready' && overview.stale && <span className="mp-chip-warning">Older than expected</span>}
      {overview.status === 'ready' && overview.refreshing && <span className="mp-chip-quiet"><Spinner /> Refreshing</span>}
    </p>
    <p className="mp-scope">{overview.description}</p>
  </div>
}

function Tiles({ overview }) {
  const { totals, activity } = overview
  const latest = activity.latest_day
  return <dl className="mp-tiles">
    <div className="mp-tile"><dt>Open listings</dt><dd>{formatCount(totals.active_listings)}</dd>
      <small>{formatCount(totals.tracked_career_listings)} in tracked tech careers</small></div>
    <div className="mp-tile"><dt>New postings{latest ? `, ${formatWeekday(latest.date)}` : ''}</dt><dd>{latest ? formatCount(latest.count) : '—'}</dd>
      <small>{activity.previous_day ? `${formatCount(activity.previous_day.count)} the day before` : 'No earlier day to compare yet'}</small></div>
    <div className="mp-tile"><dt>Daily average</dt><dd>{activity.daily_average == null ? '—' : formatCount(Math.round(activity.daily_average))}</dd>
      <small>{activity.window_days ? `New postings over the last ${activity.window_days} full days` : 'Needs one full day of data'}</small></div>
    <div className="mp-tile"><dt>Companies hiring</dt><dd>{formatCount(totals.companies)}</dd>
      <small>{formatCount(totals.remote_listings)} listings are remote</small></div>
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

function PulseSkeleton() {
  return <div className="mp-grid" aria-hidden="true">
    {[0, 1, 2, 3].map(index => <div key={index} className={`card mp-card ${index < 2 ? 'mp-span' : ''}`}>
      <Bone w="34%" h={16} /><Bone w="58%" h={10} className="sk-gap" />
      {[92, 80, 71, 60].map(width => <Bone key={width} w={`${width}%`} h={12} className="sk-gap" />)}
    </div>)}
  </div>
}

function Dashboard({ data }) {
  const { overview, trending, salary, skills, daily, weekly } = data
  if (!overview.totals.active_listings) {
    return <div className="card mp-notice" role="status"><span className="mp-notice-icon"><Icon name="alert" size={20} /></span><div>
      <strong>No listings for this market right now</strong>
      <p>None of the connected job boards returned listings for the {overview.label} market in the latest collection. Nothing is shown rather than an estimate.</p>
    </div></div>
  }
  return <div className="mp-grid">
    <Panel className="mp-span" title="Trending careers" hint={`Top 10 of ${trending.tracked_careers ?? '—'} tracked careers by open listings`} panel={trending}>
      {() => <TrendingTable trending={trending} />}
    </Panel>
    <Panel className="mp-span" title="Market trends" hint="New job postings by posting date" panel={daily.error ? daily : weekly}>
      {() => <Trends daily={daily} weekly={weekly} />}
    </Panel>
    <Panel title="Career growth" hint="Latest 7-day average vs the previous 7 days" panel={trending}>
      {() => <Growth trending={trending} />}
    </Panel>
    <Panel title="Skill demand" hint={skills.listings_with_skills ? `Share of the ${formatCount(skills.listings_with_skills)} listings that name a tracked skill` : 'Most requested technical skills'} panel={skills}>
      {() => <Skills skills={skills} />}
    </Panel>
    <Panel className="mp-span" title="Salary insights" hint="Median disclosed annual pay by career, USD" panel={salary}>
      {() => <Salaries salary={salary} />}
    </Panel>
  </div>
}

// A dashboard card. `children` is a function so a panel whose request failed never renders its body.
function Panel({ title, hint, panel, className = '', children }) {
  return <article className={`card mp-card ${className}`}>
    <header><h3>{title}</h3><p>{hint}</p></header>
    {panel.error ? <p className="mp-empty" role="alert"><Icon name="alert" size={16} />This panel could not be loaded: {panel.error}</p> : children()}
  </article>
}

function Delta({ growth }) {
  if (growth.pct == null) {
    const why = growth.reason === 'low_volume' ? 'Too few postings last week for a reliable percentage' : 'Not enough collected history yet'
    return <span className="mp-delta is-none" title={why}><span aria-hidden="true">—</span><span className="sr-only">{why}</span></span>
  }
  const word = growth.direction === 'up' ? 'Up' : growth.direction === 'down' ? 'Down' : 'No change'
  return <span className={`mp-delta is-${growth.direction}`}>
    <svg width="9" height="9" viewBox="0 0 10 10" aria-hidden="true">{growth.direction === 'flat' ? <rect x="1" y="4" width="8" height="2" rx="1" /> : <path d={growth.direction === 'up' ? 'M5 1 9.5 9h-9Z' : 'M5 9 .5 1h9Z'} />}</svg>
    <span className="sr-only">{word} </span>{formatPercent(growth.pct)}
  </span>
}

function Sparkline({ trend }) {
  const values = trend.map(point => point.new_postings)
  const max = Math.max(...values, 0)
  if (values.length < 2 || max === 0) return <span className="mp-muted" aria-hidden="true">—</span>
  const x = index => 2 + (index / (values.length - 1)) * 92
  const y = value => 21 - (value / max) * 18
  return <svg className="mp-spark" width="96" height="24" viewBox="0 0 96 24" aria-hidden="true">
    <polyline points={values.map((value, index) => `${x(index).toFixed(1)},${y(value).toFixed(1)}`).join(' ')} />
    <circle cx={x(values.length - 1)} cy={y(values[values.length - 1])} r="2.5" />
  </svg>
}

function TrendingTable({ trending }) {
  const top = trending.careers.slice(0, 10)
  if (!top.length) return <p className="mp-empty">No listing in this market matched a tracked career in the latest collection.</p>
  const peak = top[0].active_listings
  const note = growthNote(trending.growth)
  return <>
    <div className="mp-table-wrap"><table className="mp-table">
      <thead><tr>
        <th scope="col" className="mp-rank">#</th><th scope="col">Career</th><th scope="col" className="mp-num">Open listings</th>
        <th scope="col" className="mp-num mp-hide-sm">New, {trending.window_days} d</th>
        <th scope="col" className="mp-hide-sm">{top[0].trend.length}-day postings</th><th scope="col" className="mp-num">Growth</th>
      </tr></thead>
      <tbody>{top.map(career => <tr key={career.career}>
        <td className="mp-rank">{String(career.rank).padStart(2, '0')}</td>
        <th scope="row">{career.career}<span className="mp-share" aria-hidden="true"><i style={{ width: `${(career.active_listings / peak) * 100}%` }} /></span></th>
        <td className="mp-num">{formatCount(career.active_listings)}<small>{career.share_pct.toFixed(1)}%</small></td>
        <td className="mp-num mp-hide-sm">{formatCount(career.new_postings)}</td>
        <td className="mp-hide-sm"><Sparkline trend={career.trend} /></td>
        <td className="mp-num"><Delta growth={career.growth} /></td>
      </tr>)}</tbody>
    </table></div>
    {note && <p className="mp-footnote">{note}</p>}
  </>
}

function Growth({ trending }) {
  const { growth, careers } = trending
  if (!growth.ready) {
    const share = Math.round((growth.days_collected / growth.days_required) * 100)
    return <div className="mp-pending">
      <strong>{growth.reason === 'gap' ? 'Growth is paused' : 'Growth percentages are not available yet'}</strong>
      <p>{growthNote(growth)}</p>
      {growth.reason !== 'gap' && <div className="mp-progress" role="progressbar" aria-label="Days of history collected" aria-valuemin={0} aria-valuemax={growth.days_required} aria-valuenow={growth.days_collected}><i style={{ width: `${share}%` }} /></div>}
      <p className="mp-footnote">{growth.method} No estimate is shown in the meantime.</p>
    </div>
  }
  const measured = careers.filter(career => career.growth.pct != null)
  const rising = measured.filter(career => career.growth.pct > 0).sort((a, b) => b.growth.pct - a.growth.pct).slice(0, 5)
  const cooling = measured.filter(career => career.growth.pct < 0).sort((a, b) => a.growth.pct - b.growth.pct).slice(0, 5)
  if (!measured.length) return <p className="mp-empty">No career had enough postings last week for a reliable percentage.</p>
  const list = (title, items, empty) => <div className="mp-movers">
    <h4>{title}</h4>
    {items.length ? <ul>{items.map(career => <li key={career.career}>
      <span>{career.career}<small>{career.growth.current_avg} per day, was {career.growth.previous_avg}</small></span><Delta growth={career.growth} />
    </li>)}</ul> : <p className="mp-muted">{empty}</p>}
  </div>
  return <>
    {list('Rising', rising, 'No career grew this week.')}
    {list('Cooling', cooling, 'No career declined this week.')}
    <p className="mp-footnote">{growth.method}</p>
  </>
}

function Skills({ skills }) {
  if (!skills.skills.length) return <p className="mp-empty">No tracked skill was mentioned in this market's listings.</p>
  const peak = skills.skills[0].listings
  return <ol className="mp-bars">{skills.skills.map(skill => <li key={skill.skill}>
    <span className="mp-bar-label">{skill.skill}</span>
    <span className="mp-bar-track" aria-hidden="true"><i style={{ width: `${(skill.listings / peak) * 100}%` }} /></span>
    <span className="mp-bar-value">{formatCount(skill.listings)}<small>{skill.share_pct == null ? '' : `${skill.share_pct.toFixed(1)}%`}</small></span>
  </li>)}</ol>
}

function Salaries({ salary }) {
  const overall = salary.overall && <p className="mp-salary-overall">
    <strong>{formatSalary(salary.overall.median)}</strong>
    <span>median across all {formatCount(salary.overall.sample_size)} listings that disclose pay, any role. Middle half: {formatSalary(salary.overall.p25)} to {formatSalary(salary.overall.p75)}.</span>
  </p>
  if (!salary.careers.length) {
    return <>
      {overall}
      <p className="mp-empty">A median by career is not available yet: only {formatCount(salary.listings_with_salary)} of {formatCount(salary.active_listings)} open listings state an annual USD salary, and each career needs at least {salary.min_sample}. No career figure is shown rather than an unreliable one.
        {salary.insufficient.length > 0 && ` Closest so far: ${salary.insufficient.slice(0, 3).map(item => `${item.career} (${item.sample_size})`).join(', ')}.`}</p>
      <p className="mp-footnote">{salary.basis}</p>
    </>
  }
  const low = Math.min(...salary.careers.map(career => career.p25))
  const high = Math.max(...salary.careers.map(career => career.p75))
  const position = value => (high === low ? 50 : ((value - low) / (high - low)) * 100)
  return <>
    {overall}
    <div className="mp-table-wrap"><table className="mp-table mp-salary">
      <thead><tr><th scope="col">Career</th><th scope="col" className="mp-hide-sm">Middle half of salaries ({formatSalary(low)} to {formatSalary(high)})</th><th scope="col" className="mp-num">Median</th><th scope="col" className="mp-num">Listings</th></tr></thead>
      <tbody>{salary.careers.map(career => <tr key={career.career}>
        <th scope="row">{career.career}</th>
        <td className="mp-hide-sm"><span className="mp-range" title={`${formatSalary(career.p25)} to ${formatSalary(career.p75)}`}>
          <i style={{ left: `${position(career.p25)}%`, width: `${Math.max(position(career.p75) - position(career.p25), 1)}%` }} />
          <b style={{ left: `${position(career.median)}%` }} />
        </span><span className="sr-only">{formatSalary(career.p25)} to {formatSalary(career.p75)}</span></td>
        <td className="mp-num"><strong>{formatSalary(career.median)}</strong></td>
        <td className="mp-num">{formatCount(career.sample_size)}</td>
      </tr>)}</tbody>
    </table></div>
    <p className="mp-footnote">
      Based on the {formatCount(salary.listings_with_salary)} of {formatCount(salary.active_listings)} open listings that disclose pay. {salary.basis}
      {salary.insufficient.length > 0 && ` Not shown (fewer than ${salary.min_sample} salaries): ${salary.insufficient.map(item => item.career).join(', ')}.`}
    </p>
  </>
}

function Trends({ daily, weekly }) {
  const [interval, setIntervalKey] = useState('daily')
  const series = interval === 'daily' ? daily : weekly
  const points = (series.points || []).map(point => ({ ...point, key: point.date || point.week_start, label: point.date ? formatWeekday(point.date) : `Week of ${formatDay(point.week_start)}` }))
  return <>
    <div className="mp-toggle" role="group" aria-label="Chart interval">
      {['daily', 'weekly'].map(key => <button key={key} type="button" aria-pressed={interval === key} className={interval === key ? 'is-active' : ''} onClick={() => setIntervalKey(key)}>{key === 'daily' ? 'Daily' : 'Weekly'}</button>)}
    </div>
    {series.error ? <p className="mp-empty" role="alert">This view could not be loaded: {series.error}</p>
      : <TrendChart points={points} bars={interval === 'weekly'} />}
    {!series.error && <details className="mp-data-table"><summary>Show these figures as a table</summary>
      <div className="mp-table-wrap"><table className="mp-table">
        <thead><tr><th scope="col">{interval === 'daily' ? 'Day' : 'Week'}</th><th scope="col" className="mp-num">New postings</th>{interval === 'daily' && <th scope="col" className="mp-num">Open listings</th>}<th scope="col">Note</th></tr></thead>
        <tbody>{points.map(point => <tr key={point.key}>
          <th scope="row">{point.label}</th><td className="mp-num">{formatCount(point.new_postings)}</td>
          {interval === 'daily' && <td className="mp-num">{point.active_listings == null ? 'Not recorded' : formatCount(point.active_listings)}</td>}
          <td>{pointNote(point) || ''}</td>
        </tr>)}</tbody>
      </table></div>
    </details>}
  </>
}

function pointNote(point) {
  if (point.days != null) return point.partial ? `Partial week, ${point.days} of 7 days` : ''
  if (point.partial) return 'Latest day, still filling up'
  if (point.backfilled) return 'From posting dates, before collection began'
  return ''
}

function useWidth() {
  const ref = useRef(null)
  const [width, setWidth] = useState(0)
  useEffect(() => {
    if (!ref.current) return undefined
    const observer = new ResizeObserver(([entry]) => setWidth(Math.round(entry.contentRect.width)))
    observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])
  return [ref, width]
}

// Single-series chart of new postings: a line for days, columns for weeks. Hover or focus a
// position for its exact value; the table below the chart carries the same numbers.
function TrendChart({ points, bars }) {
  const [ref, width] = useWidth()
  const [active, setActive] = useState(null)
  const height = 240
  const pad = { top: 14, right: 12, bottom: 30, left: 46 }
  const inner = { width: Math.max(width - pad.left - pad.right, 10), height: height - pad.top - pad.bottom }
  const ticks = niceTicks(Math.max(...points.map(point => point.new_postings), 1))
  const top = ticks[ticks.length - 1]
  const band = inner.width / Math.max(points.length, 1)
  const x = index => pad.left + band * (index + 0.5)
  const y = value => pad.top + inner.height - (value / top) * inner.height
  const solid = points.map((point, index) => ({ ...point, index })).filter(point => bars || !point.partial)
  const line = solid.map(point => `${x(point.index).toFixed(1)},${y(point.new_postings).toFixed(1)}`).join(' ')
  const backfilled = bars ? 0 : points.filter(point => point.backfilled).length
  const every = Math.max(1, Math.ceil(points.length / Math.max(Math.floor(inner.width / 78), 1)))
  const barWidth = Math.min(24, band * 0.6)
  const focus = points[active]
  const hasPartial = points.some(point => point.partial)

  function onKeyDown(event) {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    event.preventDefault()
    const from = active ?? (event.key === 'ArrowLeft' ? points.length : -1)
    setActive(Math.min(points.length - 1, Math.max(0, from + (event.key === 'ArrowLeft' ? -1 : 1))))
  }

  return <div className="mp-chart" ref={ref}>
    {width > 0 && points.length > 0 && <svg width={width} height={height} role="img" tabIndex={0}
      aria-label={`New job postings per ${bars ? 'week' : 'day'}. Use the left and right arrow keys to read each value, or open the table below.`}
      onKeyDown={onKeyDown} onBlur={() => setActive(null)} onPointerLeave={() => setActive(null)}
      onPointerMove={event => { const box = event.currentTarget.getBoundingClientRect(); setActive(Math.min(points.length - 1, Math.max(0, Math.floor((event.clientX - box.left - pad.left) / band)))) }}>
      {backfilled > 0 && <rect className="mp-chart-backfill" x={pad.left} y={pad.top} width={band * backfilled} height={inner.height} />}
      {ticks.map(tick => <g key={tick}>
        <line className="mp-chart-grid" x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} />
        <text className="mp-chart-tick" x={pad.left - 8} y={y(tick)} dy="0.32em" textAnchor="end">{top >= 10000 ? formatCompact(tick) : formatCount(tick)}</text>
      </g>)}
      {points.map((point, index) => (index % every === 0) && <text key={point.key} className="mp-chart-tick" x={x(index)} y={height - 9} textAnchor="middle">{formatDay(point.key)}</text>)}
      {focus && !bars && <line className="mp-chart-cross" x1={x(active)} x2={x(active)} y1={pad.top} y2={pad.top + inner.height} />}
      {bars ? points.map((point, index) => {
        const barHeight = Math.max(inner.height - (y(point.new_postings) - pad.top), 0)
        const radius = Math.min(4, barHeight)
        const left = x(index) - barWidth / 2
        const base = pad.top + inner.height
        return <path key={point.key} className={`mp-chart-bar ${point.partial ? 'is-partial' : ''} ${active === index ? 'is-active' : ''}`}
          d={`M${left},${base} V${base - barHeight + radius} Q${left},${base - barHeight} ${left + radius},${base - barHeight} H${left + barWidth - radius} Q${left + barWidth},${base - barHeight} ${left + barWidth},${base - barHeight + radius} V${base} Z`} />
      }) : <>
        {solid.length > 1 && <polygon className="mp-chart-area" points={`${x(solid[0].index)},${pad.top + inner.height} ${line} ${x(solid[solid.length - 1].index)},${pad.top + inner.height}`} />}
        {solid.length > 1 && <polyline className="mp-chart-line" points={line} />}
        {points.map((point, index) => (point.partial || index === active || solid.length === 1 || index === solid[solid.length - 1]?.index)
          && <circle key={point.key} className={`mp-chart-dot ${point.partial ? 'is-partial' : ''}`} cx={x(index)} cy={y(point.new_postings)} r={index === active ? 5 : 4} />)}
      </>}
    </svg>}
    {focus && <div className="mp-tooltip" role="status" style={{ left: `${Math.min(Math.max(x(active), 96), Math.max(width - 96, 96))}px` }}>
      <strong>{formatCount(focus.new_postings)} <span>new postings</span></strong>
      <span>{focus.label}</span>
      {focus.active_listings != null && <span>{formatCount(focus.active_listings)} open listings recorded</span>}
      {pointNote(focus) && <em>{pointNote(focus)}</em>}
    </div>}
    {(backfilled > 0 || hasPartial) && <p className="mp-legend">
      {backfilled > 0 && <span><i className="mp-key-backfill" />From posting dates, before collection began</span>}
      {hasPartial && <span><i className={bars ? 'mp-key-partial-bar' : 'mp-key-partial-dot'} />{bars ? 'Partial week' : 'Latest day, still filling up'}</span>}
    </p>}
  </div>
}

function Sources({ overview }) {
  const collected = overview.collection
  const state = source => (!source.configured ? ['is-off', 'Not connected'] : !collected ? ['is-off', 'Waiting'] : source.partial ? ['is-partial', 'Partial'] : source.ok ? ['is-ok', 'Collected'] : ['is-failed', 'Failed'])
  return <footer className="mp-sources">
    <h3>Data sources</h3>
    <ul>{overview.sources.map(source => {
      const [tone, label] = state(source)
      return <li key={source.source}>
        <span className={`mp-source-state ${tone}`}><i aria-hidden="true" />{label}</span>
        <span><a href={source.url} target="_blank" rel="noreferrer">{source.label}</a>{collected && source.configured && <> · {formatCount(source.fetched)} listings</>}
          <small>{source.coverage}{source.error && source.configured ? ` Last error: ${source.error}` : ''}</small></span>
      </li>
    })}</ul>
    <p>
      {collected && <>{formatCount(collected.unique_listings)} unique listings in the latest collection after removing {formatCount(collected.duplicates_removed)} duplicates. </>}
      Figures describe listings on these job boards, not the whole labour market, and are refreshed about every {overview.refresh_interval_hours} hours. Careers and skills are matched from job titles and descriptions.
    </p>
  </footer>
}
