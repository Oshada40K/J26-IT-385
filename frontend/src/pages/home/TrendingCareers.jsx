// Trending careers: ranked by open listings, with filter chips, sorting, an expandable list
// and a per-career detail row. Growth shows "Collecting data" until 14 days exist.
import { Fragment, useMemo, useState } from 'react'
import { CATEGORY_NAMES, categoryOf, sortCareers } from './homeUtils.js'
import { formatCount, formatDay, formatSalary, growthNote } from './marketApi.js'
import { CardHeader, Delta, Segmented, Sparkline, useSeen } from './ui.jsx'

const DEFAULT_ROWS = 10

export default function TrendingCareers({ trending, salary }) {
  const [category, setCategory] = useState('All')
  const [sort, setSort] = useState('listings')
  const [showAll, setShowAll] = useState(false)
  const [open, setOpen] = useState(null)
  const [ref, seen] = useSeen(0.1)
  const careers = trending.careers
  const counts = useMemo(() => Object.fromEntries(CATEGORY_NAMES.map(name => [name, careers.filter(c => categoryOf(c.career) === name).length])), [careers])
  const filtered = useMemo(() => sortCareers(careers.filter(c => category === 'All' || categoryOf(c.career) === category), sort), [careers, category, sort])
  const rows = showAll ? filtered : filtered.slice(0, DEFAULT_ROWS)
  const peak = Math.max(...careers.map(c => c.active_listings), 1)
  const salaries = Object.fromEntries((salary?.careers || []).map(item => [item.career, item]))
  const thin = Object.fromEntries((salary?.insufficient || []).map(item => [item.career, item.sample_size]))
  const days = careers[0]?.trend.length || 0
  const note = growthNote(trending.growth)

  if (!careers.length) return <section id="trending-careers" className="card mp-card"><CardHeader title="Trending careers" /><p className="mp-empty">No listing in this market matched a tracked career in the latest collection.</p></section>

  return <section id="trending-careers" className="card mp-card trending" aria-labelledby="trending-title" ref={ref}>
    <CardHeader id="trending-title" title="Trending careers" hint={`${careers.length} tracked careers, ranked by open listings`}>
      <Segmented label="Sort careers by" value={sort} onChange={setSort} options={[
        { value: 'listings', label: 'Listings' },
        { value: 'new', label: 'New' },
        { value: 'growth', label: 'Growth', disabled: !trending.growth.ready, title: trending.growth.ready ? undefined : 'Available after 14 days of collection' },
      ]} />
    </CardHeader>
    <div className="chips" role="group" aria-label="Filter by category">
      {['All', ...CATEGORY_NAMES].map(name => <button key={name} type="button" aria-pressed={category === name} className={category === name ? 'is-active' : ''}
        disabled={name !== 'All' && !counts[name]} onClick={() => { setCategory(name); setOpen(null) }}>
        {name}<small>{name === 'All' ? careers.length : counts[name]}</small></button>)}
    </div>
    <div className="table-wrap"><table className={`mp-table trending-table ${seen ? 'is-in' : ''} ${trending.growth.ready ? '' : 'growth-pending'}`}>
      <thead><tr>
        <th scope="col" className="col-rank">#</th><th scope="col">Career</th><th scope="col" className="num">Open listings</th>
        <th scope="col" className="num hide-sm">New, {trending.window_days} d</th><th scope="col" className="hide-sm">{days}-day postings</th>
        <th scope="col" className="num col-growth">Growth</th><th scope="col"><span className="sr-only">Details</span></th>
      </tr></thead>
      <tbody>{rows.map((career, index) => {
        const expanded = open === career.career
        const detailId = `career-detail-${career.rank}`
        return <Fragment key={career.career}>
          <tr className={`trend-row ${expanded ? 'is-open' : ''}`} style={{ '--i': index }}>
            <td className="col-rank">{String(career.rank).padStart(2, '0')}</td>
            <th scope="row"><span className="career-name">{career.career}</span><span className="share" aria-hidden="true"><i style={{ '--w': career.active_listings / peak }} /></span></th>
            <td className="num"><strong>{formatCount(career.active_listings)}</strong><small>{career.share_pct.toFixed(1)}%</small></td>
            <td className="num hide-sm">{formatCount(career.new_postings)}</td>
            <td className="hide-sm"><Sparkline values={career.trend.map(p => p.new_postings)} labels={career.trend.map(p => formatDay(p.date))} format={v => `${formatCount(v)} new`} interactive /></td>
            <td className="num col-growth"><Delta growth={career.growth} /></td>
            <td className="col-action"><button type="button" className="view-career" aria-expanded={expanded} aria-controls={detailId} onClick={() => setOpen(expanded ? null : career.career)}>
              <span className="view-label" aria-hidden="true">{expanded ? 'Hide' : 'View'}</span><span className="sr-only"> {expanded ? 'Hide' : 'View'} {career.career}</span><span aria-hidden="true" className="view-arrow">→</span></button></td>
          </tr>
          {expanded && <tr className="trend-detail" id={detailId}><td colSpan={7}><CareerDetail career={career} salary={salaries[career.career]} thin={thin[career.career]} windowDays={trending.window_days} /></td></tr>}
        </Fragment>
      })}</tbody>
    </table></div>
    <div className="trending-foot">
      {filtered.length > DEFAULT_ROWS && <button type="button" className="link-button" aria-expanded={showAll} onClick={() => setShowAll(value => !value)}>
        {showAll ? 'Show top 10' : `Show all ${filtered.length} careers`}</button>}
      {note && <p className="footnote">{note}</p>}
    </div>
  </section>
}

function CareerDetail({ career, salary, thin, windowDays }) {
  const max = Math.max(...career.trend.map(p => p.new_postings), 1)
  return <div className="career-detail">
    <div>
      <h4>{career.career}</h4>
      <p>{formatCount(career.active_listings)} open listings, {career.share_pct.toFixed(1)}% of tracked tech-career listings. {formatCount(career.new_postings)} new in the last {windowDays} full days.</p>
      <p>{salary ? <>Median disclosed salary <strong>{formatSalary(salary.median)}</strong> (middle half {formatSalary(salary.p25)} to {formatSalary(salary.p75)}, {salary.sample_size} listings).</>
        : thin ? `No salary median yet: only ${thin} open listing${thin === 1 ? '' : 's'} in this career state${thin === 1 ? 's' : ''} an annual USD salary, and at least 5 are needed.`
          : 'No salary median: no open listing in this career states an annual USD salary.'}</p>
      <p>{career.growth.pct != null ? `Average daily postings: ${career.growth.current_avg} this week, ${career.growth.previous_avg} the week before.` : 'Growth appears once two full weeks of postings are collected.'}</p>
    </div>
    <figure className="mini-columns" aria-label={`New postings per day for ${career.career}`}>
      <div className="mini-columns-plot">{career.trend.map(point => <span key={point.date} title={`${formatDay(point.date)}: ${point.new_postings} new`}>
        <i style={{ '--h': point.new_postings / max }} /></span>)}</div>
      <figcaption>New postings per day, {formatDay(career.trend[0]?.date)} to {formatDay(career.trend[career.trend.length - 1]?.date)}</figcaption>
      <table className="sr-only"><tbody>{career.trend.map(point => <tr key={point.date}><th scope="row">{formatDay(point.date)}</th><td>{point.new_postings}</td></tr>)}</tbody></table>
    </figure>
  </div>
}
