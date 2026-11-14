// Where the market data comes from: one card per job board with its status in the latest
// collection, listing count, coverage and the time of that collection.
import { formatCount, formatUpdated } from './marketApi.js'
import { RevealItem, Reveal } from './MotionRoot.jsx'

const STATE = source => (!source.configured ? ['is-off', 'Not connected'] : source.partial ? ['is-partial', 'Partial'] : source.ok ? ['is-ok', 'Collected'] : ['is-failed', 'Failed'])

export default function DataSources({ overview }) {
  const collected = overview.collection
  return <Reveal as="section" id="data-sources" className="sources" aria-labelledby="sources-title">
    <h3 id="sources-title">Data sources</h3>
    <ul>{overview.sources.map(source => {
      const [tone, label] = collected ? STATE(source) : ['is-off', 'Waiting']
      return <RevealItem as="li" key={source.source} className="source-card">
        <span className={`source-state ${tone}`}><i aria-hidden="true" />{label}</span>
        <a href={source.url} target="_blank" rel="noreferrer">{source.label}</a>
        {collected && source.configured && <strong>{formatCount(source.fetched)} <span>listings</span></strong>}
        <p>{source.coverage}</p>
        {source.error && source.configured && <p className="source-error">Last error: {source.error}</p>}
        <small>Last collection: {formatUpdated(overview.last_updated)}</small>
      </RevealItem>
    })}</ul>
    <p className="footnote">
      {collected && <>{formatCount(collected.unique_listings)} unique listings in the latest collection after removing {formatCount(collected.duplicates_removed)} duplicates. </>}
      Figures describe listings on these job boards, not the whole labour market, and are refreshed about every {overview.refresh_interval_hours} hours. Careers and skills are matched from job titles and descriptions.
    </p>
  </Reveal>
}
