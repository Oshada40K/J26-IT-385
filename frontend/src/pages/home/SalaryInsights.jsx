// Salary insights: the overall median counts up; each career's middle half (25th-75th
// percentile) opens out from its median. Hover or focus a row for the exact figures.
import { useState } from 'react'
import { formatCount, formatSalary } from './marketApi.js'
import { CardHeader, CountUp, Disclosure, Segmented, useSeen } from './ui.jsx'

export default function SalaryInsights({ salary }) {
  const [sort, setSort] = useState('median')
  const [ref, seen] = useSeen(0.15)
  const careers = [...salary.careers].sort((a, b) => (sort === 'median' ? b.median - a.median : b.sample_size - a.sample_size || b.median - a.median))
  const low = Math.min(...careers.map(c => c.p25))
  const high = Math.max(...careers.map(c => c.p75))
  const at = value => (high === low ? 50 : ((value - low) / (high - low)) * 100)
  return <section id="salary-insights" className="card mp-card salary" aria-labelledby="salary-title">
    <CardHeader id="salary-title" title="Salary insights" hint="Median disclosed annual pay, USD">
      {careers.length > 1 && <Segmented label="Sort salaries by" value={sort} onChange={setSort} options={[{ value: 'median', label: 'Median' }, { value: 'listings', label: 'Listings' }]} />}
    </CardHeader>
    {salary.overall ? <div className="salary-hero">
      <span className="salary-big"><CountUp value={salary.overall.median} format={v => formatSalary(Math.round(v / 100) * 100)} /></span>
      <span>median across all {formatCount(salary.overall.sample_size)} listings that disclose pay, any role.<br />Middle half: {formatSalary(salary.overall.p25)} to {formatSalary(salary.overall.p75)}.</span>
    </div> : <p className="mp-empty">Fewer than {salary.min_sample} open listings in this market state an annual USD salary, so no overall median is shown.</p>}
    {careers.length ? <div className="table-wrap"><table className={`mp-table salary-table ${seen ? 'is-in' : ''}`} ref={ref}>
      <thead><tr><th scope="col">Career</th><th scope="col" className="hide-sm">Middle half of salaries ({formatSalary(low)} to {formatSalary(high)})</th><th scope="col" className="num">Median</th><th scope="col" className="num">Listings</th></tr></thead>
      <tbody>{careers.map((career, index) => {
        const summary = `${career.career}: 25th percentile ${formatSalary(career.p25)}, median ${formatSalary(career.median)}, 75th percentile ${formatSalary(career.p75)}, from ${career.sample_size} listings`
        return <tr key={career.career} tabIndex={0} aria-label={summary} style={{ '--i': index }}>
          <th scope="row">{career.career}</th>
          <td className="hide-sm"><span className="iqr" aria-hidden="true">
            <i style={{ left: `${at(career.p25)}%`, width: `${Math.max(at(career.p75) - at(career.p25), 1)}%`, transformOrigin: `${((career.median - career.p25) / Math.max(career.p75 - career.p25, 1)) * 100}% 50%` }} />
            <b style={{ left: `${at(career.median)}%` }} />
          </span>
          <span className="iqr-tip" aria-hidden="true">{formatSalary(career.p25)} · <strong>{formatSalary(career.median)}</strong> · {formatSalary(career.p75)} · {career.sample_size} listings</span></td>
          <td className="num"><strong>{formatSalary(career.median)}</strong></td>
          <td className="num">{formatCount(career.sample_size)}</td>
        </tr>
      })}</tbody>
    </table></div> : <p className="mp-empty">A median by career is not available yet: each career needs at least {salary.min_sample} listings that state an annual USD salary.
      {salary.insufficient.length > 0 && ` Closest so far: ${salary.insufficient.slice(0, 3).map(item => `${item.career} (${item.sample_size})`).join(', ')}.`}</p>}
    <Disclosure summary="How we calculate this">
      <p className="footnote">Based on the {formatCount(salary.listings_with_salary)} of {formatCount(salary.active_listings)} open listings that disclose pay. {salary.basis} The middle half is the 25th to 75th percentile. A career needs at least {salary.min_sample} salaries for a median.</p>
      {salary.insufficient.length > 0 && <p className="footnote">Not shown (fewer than {salary.min_sample} salaries): {salary.insufficient.map(item => `${item.career} (${item.sample_size})`).join(', ')}.</p>}
    </Disclosure>
  </section>
}
