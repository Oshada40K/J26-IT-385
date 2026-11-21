// One headline figure in the Market Pulse band: counts up on first view and between markets.
// The delta chip and sparkline appear only when the backend has the earlier days to compare.
import { CountUp, Sparkline } from './ui.jsx'
import { formatCount } from './marketApi.js'

export default function KpiTile({ label, value, note, delta, deltaLabel, spark, sparkLabels, sparkFormat = formatCount }) {
  const direction = delta ? (delta.value > 0 ? 'up' : delta.value < 0 ? 'down' : 'flat') : null
  const sign = n => (n > 0 ? '+' : n < 0 ? '−' : '')
  return <div className="kpi">
    <dt>{label}</dt>
    <dd>
      <span className="kpi-value"><CountUp value={value} format={v => formatCount(Math.round(v))} /></span>
      {(delta || spark) && <span className="kpi-foot">
        {delta && <span className={`kpi-delta is-${direction}`}>
          <svg width="8" height="8" viewBox="0 0 10 10" aria-hidden="true">{direction === 'flat' ? <rect x="1" y="4" width="8" height="2" rx="1" /> : <path d={direction === 'up' ? 'M5 1 9.5 9h-9Z' : 'M5 9 .5 1h9Z'} />}</svg>
          {sign(delta.value)}{formatCount(Math.abs(delta.value))}{delta.pct != null && ` (${sign(delta.pct)}${Math.abs(delta.pct)}%)`}
          <span className="sr-only"> {deltaLabel}</span>
        </span>}
        {spark && <Sparkline values={spark} labels={sparkLabels} format={sparkFormat} interactive width={84} height={24} className="kpi-spark" />}
      </span>}
      {note && <small className="kpi-note">{note}</small>}
    </dd>
  </div>
}
