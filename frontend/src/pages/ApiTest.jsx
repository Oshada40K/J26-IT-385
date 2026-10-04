// API connectivity test page (frontend -> FastAPI backend).
// Testing only: no real component logic here.
import { useState } from 'react'
import { API_BASE_URL, apiGet } from '../api/client.js'

const apis = [
  { id: 'root', title: 'Backend Root', name: '', short: 'Backend Root', endpoint: '/' },
  { id: 'health', title: 'Backend Health', name: '', short: 'Backend Health', endpoint: '/health' },
  { id: 'skill', title: 'Component 01', name: 'Technical Skill Profile', short: 'Component 01', endpoint: '/api/skill/test' },
  { id: 'personality', title: 'Component 02', name: 'Personality Profile', short: 'Component 02', endpoint: '/api/personality/test' },
  { id: 'career', title: 'Component 03', name: 'Explainable Career Recommendation', short: 'Component 03', endpoint: '/api/career/test' },
  { id: 'roadmap', title: 'Component 04', name: 'Learning Roadmap & Skill Gap', short: 'Component 04', endpoint: '/api/roadmap/test' },
]

const STATUS = {
  idle: 'Not tested',
  testing: 'Testing...',
  ok: 'Connected',
  fail: 'Connection Failed',
}


const styles = {
  card: { background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 16, padding: 24, marginBottom: 20 },
  button: { padding: '8px 14px', border: 'none', borderRadius: 8, background: 'var(--color-primary)', color: 'var(--color-surface)', cursor: 'pointer' },
  buttonDisabled: { opacity: 0.6, cursor: 'not-allowed' },
  pre: { background: 'var(--color-background)', border: '1px solid var(--color-border)', borderRadius: 8, padding: 10, overflowX: 'auto', fontSize: 11 },
  error: { color: 'var(--color-danger-text)', margin: '8px 0' },
  summaryRow: { display: 'flex', justifyContent: 'space-between', maxWidth: 360, padding: '4px 0', borderBottom: '1px solid var(--color-border)' },
}

function describeError(err) {
  // fetch() throws a TypeError when the server is unreachable or the request is blocked by CORS.
  if (err instanceof TypeError) {
    if (new URL(API_BASE_URL).hostname.endsWith('.railway.internal')) {
      return 'The backend URL is a private Railway address. Set VITE_API_BASE_URL to the backend public HTTPS domain from Railway Settings > Networking, then restart or rebuild the frontend.'
    }
    return `Unable to connect to backend at ${API_BASE_URL}. Check that this URL is reachable from your browser and that CORS allows this origin (${window.location.origin}).`
  }
  return err?.message || 'Unknown error'
}

function StatusBadge({ status }) {
  return <span className={`status-badge status-${status}`} role="status">{STATUS[status]}</span>
}

const initialResults = Object.fromEntries(apis.map((a) => [a.id, { status: 'idle', data: null, error: null }]))

export default function ApiTest() {
  const [results, setResults] = useState(initialResults)
  const [testingAll, setTestingAll] = useState(false)
  const [summary, setSummary] = useState(null)

  function setResult(id, value) {
    setResults((prev) => ({ ...prev, [id]: value }))
  }

  // Never throws: each API result is isolated so one failure cannot break the page.
  async function testApi(api) {
    setResult(api.id, { status: 'testing', data: null, error: null })
    try {
      const data = await apiGet(api.endpoint)
      setResult(api.id, { status: 'ok', data, error: null })
      return 'ok'
    } catch (err) {
      setResult(api.id, { status: 'fail', data: null, error: describeError(err) })
      return 'fail'
    }
  }

  async function testAll() {
    setTestingAll(true)
    setSummary(null)
    const outcomes = await Promise.all(apis.map(testApi))
    setSummary(apis.map((api, i) => ({ label: api.short, status: outcomes[i] })))
    setTestingAll(false)
  }

  const allOk = summary?.every((s) => s.status === 'ok')

  return (
    <div className="page">
      <p className="eyebrow">WORKSPACE / SYSTEM CONNECTIVITY</p>
      <h1 style={{ marginTop: 0 }}>API integration test</h1>
      <p className="page-description">Check the connection between your workspace and each research component.</p>
      <p>
        Backend: <code>{API_BASE_URL}</code> ·{' '}
        <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">
          Open Swagger UI (/docs)
        </a>
      </p>

      <div className="card api-card" style={styles.card}>
        <button
          style={{ ...styles.button, ...(testingAll ? styles.buttonDisabled : {}) }}
          onClick={testAll}
          disabled={testingAll}
        >
          {testingAll ? 'Testing...' : 'Test All APIs'}
        </button>

        {summary && (
          <div style={{ marginTop: 16 }}>
            {summary.map((s) => (
              <div key={s.label} style={styles.summaryRow}>
                <span>{s.label}</span>
                <StatusBadge status={s.status} />
              </div>
            ))}
            <p style={{ fontWeight: 'bold', color: allOk ? 'var(--color-success-text)' : 'var(--color-danger-text)' }}>
              {allOk ? 'All backend APIs are connected successfully.' : 'Some backend APIs could not be reached.'}
            </p>
          </div>
        )}
      </div>

      {apis.map((api) => {
        const r = results[api.id]
        const busy = r.status === 'testing'
        return (
          <div key={api.id} className="card api-card" style={styles.card}>
            <h3 style={{ margin: '0 0 4px' }}>
              {api.title}
              {api.name && ` - ${api.name}`}
            </h3>
            <p style={{ margin: '0 0 8px', color: 'var(--color-text-secondary)' }}>
              GET <code>{api.endpoint}</code>
            </p>
            <p>
              Status: <StatusBadge status={r.status} />
            </p>

            {r.status === 'ok' && (
              <>
                <div>Response:</div>
                <pre style={styles.pre}>{JSON.stringify(r.data, null, 2)}</pre>
              </>
            )}
            {r.status === 'fail' && <p role="alert" style={styles.error}>{r.error}</p>}

            <button
              style={{ ...styles.button, ...(busy ? styles.buttonDisabled : {}) }}
              onClick={() => testApi(api)}
              disabled={busy}
            >
              {busy ? 'Testing...' : 'Test API'}
            </button>
          </div>
        )
      })}
    </div>
  )
}
