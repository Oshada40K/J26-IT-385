// Career growth: a progress ring until two full weeks are collected, then a diverging bar
// chart of the latest 7-day average against the previous 7 days, per career.
import { formatPercent, growthNote } from './marketApi.js'
import { CardHeader, useSeen } from './ui.jsx'

export default function CareerGrowth({ trending }) {
  const { growth, careers } = trending
  return <section className="card mp-card" aria-labelledby="growth-title">
    <CardHeader id="growth-title" title="Career growth" hint="Latest 7-day average vs the previous 7 days" />
    {growth.ready ? <Diverging careers={careers} method={growth.method} /> : <Pending growth={growth} />}
  </section>
}

function Pending({ growth }) {
  const [ref, seen] = useSeen(0.4)
  const share = growth.days_required ? growth.days_collected / growth.days_required : 0
  const r = 44
  const length = 2 * Math.PI * r
  const left = growth.days_required - growth.days_collected
  return <div className="growth-pending" ref={ref}>
    <div className="ring" role="progressbar" aria-label="Days of history collected" aria-valuemin={0} aria-valuemax={growth.days_required} aria-valuenow={growth.days_collected}>
      <svg width="112" height="112" viewBox="0 0 112 112" aria-hidden="true">
        <circle className="ring-track" cx="56" cy="56" r={r} />
        <circle className="ring-fill" cx="56" cy="56" r={r} strokeDasharray={length} strokeDashoffset={seen ? length * (1 - share) : length} />
      </svg>
      <span className="ring-label"><strong>{growth.days_collected}</strong><small>of {growth.days_required} days</small></span>
    </div>
    <div>
      <strong>{growth.reason === 'gap' ? 'Growth is paused' : 'Growth percentages are not available yet'}</strong>
      <p>{growth.reason === 'gap' ? growthNote(growth) : `${growth.days_collected} of ${growth.days_required} days collected, ${left} to go.`}</p>
      <p className="footnote">{growth.method} No estimate is shown in the meantime.</p>
    </div>
  </div>
}

function Diverging({ careers, method }) {
  const [ref, seen] = useSeen(0.2)
  const measured = careers.filter(career => career.growth.pct != null).sort((a, b) => b.growth.pct - a.growth.pct)
  if (!measured.length) return <p className="mp-empty">No career had enough postings last week for a reliable percentage.</p>
  const shown = measured.length > 12 ? [...measured.slice(0, 6), ...measured.slice(-6)] : measured
  const limit = Math.max(...shown.map(career => Math.abs(career.growth.pct)), 1)
  return <>
    <ul className={`diverging ${seen ? 'is-in' : ''}`} ref={ref} aria-label="Growth by career">
      {shown.map((career, index) => {
        const pct = career.growth.pct
        return <li key={career.career} style={{ '--i': index }}>
          <span className="diverging-label">{career.career}</span>
          <span className="diverging-track" aria-hidden="true">
            <i className={pct >= 0 ? 'is-up' : 'is-down'} style={{ '--w': Math.abs(pct) / limit }} />
          </span>
          <span className={`diverging-value ${pct > 0 ? 'is-up' : pct < 0 ? 'is-down' : ''}`}>
            <span aria-hidden="true">{pct > 0 ? '▲' : pct < 0 ? '▼' : '■'}</span> {formatPercent(pct)}
            <span className="sr-only"> ({career.growth.current_avg} per day, was {career.growth.previous_avg})</span>
          </span>
        </li>
      })}
    </ul>
    {measured.length > shown.length && <p className="footnote">Showing the 6 fastest-rising and 6 fastest-cooling of {measured.length} careers with enough postings.</p>}
    <p className="footnote">{method}</p>
  </>
}
