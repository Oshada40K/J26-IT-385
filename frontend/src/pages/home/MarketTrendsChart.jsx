// New postings over time: a line for days, columns for weeks. Days before collection began are
// shaded; the latest partial day is a hollow, softly pulsing dot. Hover, focus + arrow keys,
// or the table below give every exact value.
import { useId, useState } from 'react'
import { formatCompact, formatCount, formatDay, formatWeekday, niceTicks } from './marketApi.js'
import { CardHeader, Disclosure, Segmented, useSeen, useWidth } from './ui.jsx'

export function pointNote(point) {
  if (point.days != null) return point.partial ? `Partial week, ${point.days} of 7 days` : ''
  if (point.partial) return 'Latest day, still filling up'
  if (point.backfilled) return 'From posting dates, before collection began'
  return ''
}

export default function MarketTrendsChart({ daily, weekly }) {
  const [interval, setIntervalKey] = useState('daily')
  const series = interval === 'daily' ? daily : weekly
  const points = (series?.points || []).map(point => ({ ...point, key: point.date || point.week_start, label: point.date ? formatWeekday(point.date) : `Week of ${formatDay(point.week_start)}` }))
  return <section className="card mp-card bento-wide" aria-labelledby="trends-title">
    <CardHeader id="trends-title" title="Market trends" hint="New job postings by posting date">
      <Segmented label="Chart interval" value={interval} onChange={setIntervalKey} options={[{ value: 'daily', label: 'Daily' }, { value: 'weekly', label: 'Weekly' }]} />
    </CardHeader>
    {series?.error ? <p className="mp-empty" role="alert">This view could not be loaded: {series.error}</p>
      : <TrendChart key={interval} points={points} bars={interval === 'weekly'} />}
    {!series?.error && <Disclosure summary="Show these figures as a table">
      <div className="table-wrap"><table className="mp-table">
        <thead><tr><th scope="col">{interval === 'daily' ? 'Day' : 'Week'}</th><th scope="col" className="num">New postings</th>{interval === 'daily' && <th scope="col" className="num">Open listings</th>}<th scope="col">Note</th></tr></thead>
        <tbody>{points.map(point => <tr key={point.key}>
          <th scope="row">{point.label}</th><td className="num">{formatCount(point.new_postings)}</td>
          {interval === 'daily' && <td className="num">{point.active_listings == null ? 'Not recorded' : formatCount(point.active_listings)}</td>}
          <td>{pointNote(point)}</td>
        </tr>)}</tbody>
      </table></div>
    </Disclosure>}
  </section>
}

function TrendChart({ points, bars }) {
  const [box, width] = useWidth()
  const [seenRef, seen] = useSeen(0.3)
  const [active, setActive] = useState(null)
  const clip = useId().replace(/:/g, '')
  const height = 250
  const pad = { top: 16, right: 14, bottom: 30, left: 46 }
  const inner = { width: Math.max(width - pad.left - pad.right, 10), height: height - pad.top - pad.bottom }
  const ticks = niceTicks(Math.max(...points.map(point => point.new_postings), 1))
  const top = ticks[ticks.length - 1]
  const band = inner.width / Math.max(points.length, 1)
  const x = index => pad.left + band * (index + 0.5)
  const y = value => pad.top + inner.height - (value / top) * inner.height
  const base = pad.top + inner.height
  const solid = points.map((point, index) => ({ ...point, index })).filter(point => bars || !point.partial)
  const line = solid.map(point => `${x(point.index).toFixed(1)},${y(point.new_postings).toFixed(1)}`).join(' ')
  const backfilled = bars ? 0 : points.filter(point => point.backfilled).length
  const every = Math.max(1, Math.ceil(points.length / Math.max(Math.floor(inner.width / 78), 1)))
  const barWidth = Math.min(24, band * 0.6)
  const focus = points[active]
  const hasPartial = points.some(point => point.partial)
  const partialIndex = points.findIndex(point => point.partial)

  function onKeyDown(event) {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
    event.preventDefault()
    const from = active ?? (event.key === 'ArrowLeft' ? points.length : -1)
    setActive(Math.min(points.length - 1, Math.max(0, from + (event.key === 'ArrowLeft' ? -1 : 1))))
  }

  if (!points.length) return <p className="mp-empty">No postings have been recorded for this period yet.</p>
  return <div className="trend-chart" ref={node => { box.current = node; seenRef.current = node }}>
    {width > 0 && <svg width={width} height={height} role="img" tabIndex={0}
      aria-label={`New job postings per ${bars ? 'week' : 'day'}. Use the left and right arrow keys to read each value, or open the table below.`}
      onKeyDown={onKeyDown} onBlur={() => setActive(null)} onPointerLeave={() => setActive(null)}
      onPointerMove={event => { const rect = event.currentTarget.getBoundingClientRect(); setActive(Math.min(points.length - 1, Math.max(0, Math.floor((event.clientX - rect.left - pad.left) / band)))) }}>
      <defs><clipPath id={clip}><rect className={`draw-clip ${seen ? 'is-in' : ''}`} x={pad.left} y="0" width={inner.width} height={height} /></clipPath></defs>
      {backfilled > 0 && <rect className="chart-backfill" x={pad.left} y={pad.top} width={band * backfilled} height={inner.height} />}
      {ticks.map(tick => <g key={tick}>
        <line className="chart-grid" x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} />
        <text className="chart-tick" x={pad.left - 8} y={y(tick)} dy="0.32em" textAnchor="end">{top >= 10000 ? formatCompact(tick) : formatCount(tick)}</text>
      </g>)}
      {points.map((point, index) => (index % every === 0) && <text key={point.key} className="chart-tick" x={x(index)} y={height - 9} textAnchor="middle">{formatDay(point.key)}</text>)}
      {focus && !bars && <line className="chart-cross" x1={x(active)} x2={x(active)} y1={pad.top} y2={base} />}
      {bars ? points.map((point, index) => {
        const barHeight = Math.max(base - y(point.new_postings), 0)
        const r = Math.min(4, barHeight)
        const left = x(index) - barWidth / 2
        return <path key={point.key} className={`chart-bar ${point.partial ? 'is-partial' : ''} ${active === index ? 'is-active' : ''} ${seen ? 'is-in' : ''}`} style={{ '--i': index }}
          d={`M${left},${base} V${base - barHeight + r} Q${left},${base - barHeight} ${left + r},${base - barHeight} H${left + barWidth - r} Q${left + barWidth},${base - barHeight} ${left + barWidth},${base - barHeight + r} V${base} Z`} />
      }) : <>
        <g clipPath={`url(#${clip})`}>
          {solid.length > 1 && <polygon className="chart-area" points={`${x(solid[0].index)},${base} ${line} ${x(solid[solid.length - 1].index)},${base}`} />}
          {solid.length > 1 && <polyline className="chart-line" points={line} />}
          {solid.length > 0 && <circle className="chart-dot" cx={x(solid[solid.length - 1].index)} cy={y(solid[solid.length - 1].new_postings)} r="4" />}
        </g>
        {partialIndex >= 0 && <g className="chart-partial">
          <circle className="chart-partial-ring" cx={x(partialIndex)} cy={y(points[partialIndex].new_postings)} r="5" />
          <circle className="chart-dot is-partial" cx={x(partialIndex)} cy={y(points[partialIndex].new_postings)} r="4.5" />
        </g>}
        {focus && <circle className="chart-dot is-focus" cx={x(active)} cy={y(focus.new_postings)} r="5" />}
      </>}
    </svg>}
    {focus && <div className="chart-tooltip" role="status" style={{ left: `${Math.min(Math.max(x(active), 100), Math.max(width - 100, 100))}px` }}>
      <strong>{formatCount(focus.new_postings)} <span>new postings</span></strong>
      <span>{focus.label}</span>
      {focus.active_listings != null && <span>{formatCount(focus.active_listings)} open listings recorded</span>}
      {pointNote(focus) && <em>{pointNote(focus)}</em>}
    </div>}
    {(backfilled > 0 || hasPartial) && <p className="chart-legend">
      {backfilled > 0 && <span><i className="key-backfill" />From posting dates, before collection began</span>}
      {hasPartial && <span><i className={bars ? 'key-partial-bar' : 'key-partial-dot'} />{bars ? 'Partial week' : 'Latest day, still filling up'}</span>}
    </p>}
  </div>
}
