// Owner: Oshada - Component 03: Explainable Career Recommendation.
// Calls the three career APIs and shows their responses. The backend builds the
// recommendation from the Component 01 and 02 profiles, so no input is sent from here.
import { useState } from 'react'
import { API_BASE_URL, apiGet } from '../../api/client.js'

const ENDPOINTS = {
  bestJob: '/api/career/best-job',
  topJobs: '/api/career/top-jobs',
  explanation: '/api/career/explanation',
}

const styles = {
  card: { background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 16, padding: 24, marginBottom: 20 },
  button: { padding: '8px 14px', border: 'none', borderRadius: 8, color: 'var(--color-surface)', cursor: 'pointer' },
  buttonDisabled: { opacity: 0.6, cursor: 'not-allowed' },
  muted: { color: 'var(--color-text-secondary)', margin: '0 0 12px' },
  error: { color: 'var(--color-danger-text)', background: 'var(--color-danger-soft)', border: '1px solid var(--color-border)', borderRadius: 8, padding: 10 },
  pre: { background: 'var(--color-background)', border: '1px solid var(--color-border)', borderRadius: 8, padding: 10, overflowX: 'auto', fontSize: 11 },
  bestJob: { fontSize: 22, fontWeight: 'bold', color: 'var(--color-primary)', margin: '8px 0' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', borderBottom: '1px solid var(--color-border)', padding: '6px 8px' },
  td: { borderBottom: '1px solid var(--color-border)', padding: '6px 8px' },
  barTrack: { background: 'var(--color-primary-soft)', borderRadius: 8, height: 10, width: '100%' },
  meta: { display: 'grid', gridTemplateColumns: 'minmax(100px, 160px) minmax(0, 1fr)', gap: '4px 16px', margin: 0 },
}

function describeError(err) {
  // fetch() throws a TypeError when the backend is unreachable or blocked by CORS.
  if (err instanceof TypeError) {
    return `Unable to connect to backend at ${API_BASE_URL}.`
  }
  // apiGet throws "API error <status>: <body>"; show FastAPI's "detail" when present.
  const match = /^API error (\d+): ([\s\S]*)$/.exec(err?.message || '')
  if (match) {
    try {
      const detail = JSON.parse(match[2]).detail
      if (detail) return `HTTP ${match[1]}: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`
    } catch {
      // Body was not JSON; fall through to the raw message.
    }
  }
  return err?.message || 'Unknown error'
}

function Button({ loading, onClick, children }) {
  return (
    <button
      className="button-ai"
      style={{ ...styles.button, ...(loading ? styles.buttonDisabled : {}) }}
      onClick={onClick}
      disabled={loading}
    >
      {loading ? 'Loading...' : children}
    </button>
  )
}

function RawJson({ data }) {
  return (
    <details style={{ marginTop: 12 }}>
      <summary style={{ cursor: 'pointer' }}>Raw JSON response</summary>
      <pre style={styles.pre}>{JSON.stringify(data, null, 2)}</pre>
    </details>
  )
}

function ApiSection({ title, endpoint, state, onLoad, children }) {
  return (
    <div className={`card api-card ${title === 'Explanation' ? 'ai-section' : ''}`} style={{ ...styles.card, background: undefined }}>
      <h2 style={{ margin: '0 0 4px' }}>{title}</h2>
      <p style={styles.muted}>
        GET <code>{endpoint}</code>
      </p>
      {state.error && <p role="alert" style={styles.error}>{state.error}</p>}
      {state.data && (
        <>
          {children(state.data)}
          <RawJson data={state.data} />
        </>
      )}
      <div style={{ marginTop: 12 }}>
        <Button loading={state.loading} onClick={onLoad}>
          {state.data ? 'Reload' : 'Load'}
        </Button>
      </div>
    </div>
  )
}

function BestJob({ data }) {
  return (
    <>
      <div className="best-match-label">Your strongest career match</div>
      <div className="best-job-name" style={styles.bestJob}>{data.best_job}</div>
      {data.unrecognised_skills?.length > 0 && (
        <p>Unrecognised skills: {data.unrecognised_skills.join(', ')}</p>
      )}
    </>
  )
}

function TopJobs({ data }) {
  return (
    <div className="table-scroll"><table style={{ ...styles.table, minWidth: 500 }}>
      <thead>
        <tr>
          <th style={styles.th}>Rank</th>
          <th style={styles.th}>Job</th>
          <th style={{ ...styles.th, width: '35%' }}>Score (0-100)</th>
        </tr>
      </thead>
      <tbody>
        {data.jobs.map((job) => (
          <tr key={job.ranking} className={job.ranking === 1 ? 'top-job-row' : ''}>
            <td style={styles.td}><span className="rank-badge">{job.ranking}</span></td>
            <td style={{ ...styles.td, fontWeight: job.ranking === 1 ? 'bold' : 'normal' }}>{job.job}</td>
            <td style={styles.td}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={styles.barTrack}>
                  <div className="score-fill" style={{ width: `${job.score}%` }} />
                </div>
                <span className="score-value" style={{ minWidth: 44, textAlign: 'right' }}>{job.score.toFixed(2)}</span>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table></div>
  )
}

function Explanation({ data }) {
  // The backend returns one paragraph; show each sentence as its own point.
  const sentences = data.explanation.split(/(?<=\.)\s+/).filter(Boolean)
  return (
    <>
      <div className="eyebrow">WHY THIS CAREER / SHAP EXPLAINABILITY</div>
      <ul className="explanation-list">
        {sentences.map((s, i) => (
          <li key={i} style={{ marginBottom: 4 }}>{s}</li>
        ))}
      </ul>
    </>
  )
}

function ModelInfo({ data }) {
  return (
    <div className="card api-card" style={styles.card}>
      <h2 style={{ margin: '0 0 12px' }}>Model information</h2>
      <dl style={styles.meta}>
        <dt>Candidate ID</dt>
        <dd style={{ margin: 0 }}>{data.candidate_id}</dd>
        <dt>Model</dt>
        <dd style={{ margin: 0 }}>{data.model_type}</dd>
        <dt>O*NET version</dt>
        <dd style={{ margin: 0 }}>{data.onet_version}</dd>
        <dt>Occupations compared</dt>
        <dd style={{ margin: 0 }}>{data.eligible_occupations}</dd>
        <dt>Score meaning</dt>
        <dd style={{ margin: 0 }}>{data.score_meaning}</dd>
      </dl>
    </div>
  )
}

const emptyState = { loading: false, data: null, error: null }

export default function CareerRecommendation() {
  const [results, setResults] = useState({ bestJob: emptyState, topJobs: emptyState, explanation: emptyState })

  async function load(key) {
    setResults((prev) => ({ ...prev, [key]: { ...prev[key], loading: true, error: null } }))
    try {
      const data = await apiGet(ENDPOINTS[key])
      setResults((prev) => ({ ...prev, [key]: { loading: false, data, error: null } }))
    } catch (err) {
      setResults((prev) => ({ ...prev, [key]: { loading: false, data: null, error: describeError(err) } }))
    }
  }

  const loadAll = () => Promise.all(Object.keys(ENDPOINTS).map(load))
  const anyLoading = Object.values(results).some((r) => r.loading)
  // All three responses share the same model metadata; show it from whichever loaded.
  const metadata = results.bestJob.data || results.topJobs.data || results.explanation.data

  return (
    <div className="page accent-career">
      <p className="eyebrow">COMPONENT 03 / EXPLAINABLE CAREER INTELLIGENCE</p>
      <h1 style={{ marginTop: 0 }}>Find your direction. Understand why.</h1>
      <p className="page-description" style={{ marginBottom: 20 }}>Explore your strongest career match, compare five ranked possibilities, and discover the evidence behind the recommendation.</p>
      <p style={styles.muted}>
        Component 03 · Backend: <code>{API_BASE_URL}</code>
      </p>
      <div style={{ marginBottom: 16 }}>
        <Button loading={anyLoading} onClick={loadAll}>
          Load all recommendations
        </Button>
      </div>

      <ApiSection title="Best Job" endpoint={ENDPOINTS.bestJob} state={results.bestJob} onLoad={() => load('bestJob')}>
        {(data) => <BestJob data={data} />}
      </ApiSection>

      <ApiSection title="Top 5 Jobs" endpoint={ENDPOINTS.topJobs} state={results.topJobs} onLoad={() => load('topJobs')}>
        {(data) => <TopJobs data={data} />}
      </ApiSection>

      <ApiSection
        title="Explanation"
        endpoint={ENDPOINTS.explanation}
        state={results.explanation}
        onLoad={() => load('explanation')}
      >
        {(data) => <Explanation data={data} />}
      </ApiSection>

      {metadata && <ModelInfo data={metadata} />}
    </div>
  )
}
