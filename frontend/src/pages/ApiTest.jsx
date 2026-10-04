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

const statusColors = {
  idle: { background: '#eee', border: '#ccc', color: '#555' },
  testing: { background: '#fff3cd', border: '#f0d58c', color: '#7a5d00' },
  ok: { background: '#d4edda', border: '#9fd3ab', color: '#1e6b33' },
  fail: { background: '#f8d7da', border: '#eba6ac', color: '#8a1c25' },
}

const styles = {
  card: { background: '#fff', border: '1px solid #ddd', borderRadius: 6, padding: 16, marginBottom: 16 },
  button: { padding: '8px 14px', border: 'none', borderRadius: 4, background: '#1f3a5f', color: '#fff', cursor: 'pointer' },
  buttonDisabled: { opacity: 0.6, cursor: 'not-allowed' },
  pre: { background: '#f5f6f8', border: '1px solid #e2e2e2', borderRadius: 4, padding: 10, overflowX: 'auto', fontSize: 13 },
  error: { color: '#8a1c25', margin: '8px 0' },
  summaryRow: { display: 'flex', justifyContent: 'space-between', maxWidth: 360, padding: '4px 0', borderBottom: '1px solid #eee' },
}

function describeError(err) {
  // fetch() throws a TypeError when the server is unreachable or the request is blocked by CORS.
  if (err instanceof TypeError) {
    return `Unable to connect to backend at ${API_BASE_URL}. Make sure the FastAPI backend is running (locally on port 8000) and that CORS allows this origin (${window.location.origin}).`
  }
  return err?.message || 'Unknown error'
}

function StatusBadge({ status }) {
  const c = statusColors[status]
  return (
    <span style={{ display: 'inline-block', padding: '3px 10px', borderRadius: 4, border: `1px solid ${c.border}`, background: c.background, color: c.color, fontWeight: 'bold' }}>
      {STATUS[status]}
    </span>
  )
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
    <div style={{ maxWidth: 800 }}>
      <h1 style={{ marginTop: 0 }}>AI-Based Smart Career Path Recommendation System</h1>
      <h2>API Integration Test</h2>
      <p>
        Backend: <code>{API_BASE_URL}</code> ·{' '}
        <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">
          Open Swagger UI (/docs)
        </a>
      </p>

      <div style={styles.card}>
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
            <p style={{ fontWeight: 'bold', color: allOk ? '#1e6b33' : '#8a1c25' }}>
              {allOk ? 'All backend APIs are connected successfully.' : 'Some backend APIs could not be reached.'}
            </p>
          </div>
        )}
      </div>

      {apis.map((api) => {
        const r = results[api.id]
        const busy = r.status === 'testing'
        return (
          <div key={api.id} style={styles.card}>
            <h3 style={{ margin: '0 0 4px' }}>
              {api.title}
              {api.name && ` - ${api.name}`}
            </h3>
            <p style={{ margin: '0 0 8px', color: '#666' }}>
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
            {r.status === 'fail' && <p style={styles.error}>{r.error}</p>}

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
