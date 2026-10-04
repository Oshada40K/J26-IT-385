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
  card: { background: '#fff', border: '1px solid #ddd', borderRadius: 6, padding: 16, marginBottom: 16 },
  button: { padding: '8px 14px', border: 'none', borderRadius: 4, background: '#1f3a5f', color: '#fff', cursor: 'pointer' },
  buttonDisabled: { opacity: 0.6, cursor: 'not-allowed' },
  muted: { color: '#666', margin: '0 0 12px' },
  error: { color: '#8a1c25', background: '#f8d7da', border: '1px solid #eba6ac', borderRadius: 4, padding: 10 },
  pre: { background: '#f5f6f8', border: '1px solid #e2e2e2', borderRadius: 4, padding: 10, overflowX: 'auto', fontSize: 13 },
  bestJob: { fontSize: 22, fontWeight: 'bold', color: '#1f3a5f', margin: '8px 0' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', borderBottom: '2px solid #ddd', padding: '6px 8px' },
  td: { borderBottom: '1px solid #eee', padding: '6px 8px' },
  barTrack: { background: '#eef2f7', borderRadius: 3, height: 10, width: '100%' },
  meta: { display: 'grid', gridTemplateColumns: 'max-content 1fr', gap: '4px 16px', margin: 0 },
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
    <div style={styles.card}>
      <h2 style={{ margin: '0 0 4px' }}>{title}</h2>
      <p style={styles.muted}>
        GET <code>{endpoint}</code>
      </p>
      {state.error && <p style={styles.error}>{state.error}</p>}
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
      <div>Best matching job:</div>
      <div style={styles.bestJob}>{data.best_job}</div>
      {data.unrecognised_skills?.length > 0 && (
        <p>Unrecognised skills: {data.unrecognised_skills.join(', ')}</p>
      )}
    </>
  )
}

function TopJobs({ data }) {
  return (
    <table style={styles.table}>
      <thead>
        <tr>
          <th style={styles.th}>Rank</th>
          <th style={styles.th}>Job</th>
          <th style={{ ...styles.th, width: '35%' }}>Score (0-100)</th>
        </tr>
      </thead>
      <tbody>
        {data.jobs.map((job) => (
          <tr key={job.ranking}>
            <td style={styles.td}>{job.ranking}</td>
            <td style={{ ...styles.td, fontWeight: job.ranking === 1 ? 'bold' : 'normal' }}>{job.job}</td>
            <td style={styles.td}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={styles.barTrack}>
                  <div style={{ background: '#1f3a5f', borderRadius: 3, height: 10, width: `${job.score}%` }} />
                </div>
                <span style={{ minWidth: 44, textAlign: 'right' }}>{job.score.toFixed(2)}</span>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function Explanation({ data }) {
  // The backend returns one paragraph; show each sentence as its own point.
  const sentences = data.explanation.split(/(?<=\.)\s+/).filter(Boolean)
  return (
    <>
      <div>Why the top job was recommended (SHAP):</div>
      <ul>
        {sentences.map((s, i) => (
          <li key={i} style={{ marginBottom: 4 }}>{s}</li>
        ))}
      </ul>
    </>
  )
}

function ModelInfo({ data }) {
  return (
    <div style={styles.card}>
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
    <div style={{ maxWidth: 900 }}>
      <h1 style={{ marginTop: 0 }}>Explainable Career Recommendation</h1>
      <p style={styles.muted}>
        Component 03 · Backend: <code>{API_BASE_URL}</code>
      </p>
      <div style={{ marginBottom: 16 }}>
        <Button loading={anyLoading} onClick={loadAll}>
          Load all
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
