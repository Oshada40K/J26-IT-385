// Privacy and research consent: consent status and toggle, data download, account deletion.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Icon from '../../components/Icon.jsx'
import { useAuth } from '../../auth/AuthContext.jsx'
import { deleteAccount, exportProfile } from './profileApi.js'
import { Modal, formatDate } from './profileUi.jsx'

// Browser-session keys the research modules use for this person's results.
const MODULE_KEYS = ['careernova-skill-session', 'careernova-personality-draft', 'careernova-c4-assessment']

export default function PrivacyTab({ data, modules, onConsent, toast, theme }) {
  const { consent, account } = data
  const [savingConsent, setSavingConsent] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [confirming, setConfirming] = useState(false)

  async function toggle() {
    setSavingConsent(true)
    try { await onConsent(!consent.research_use) } finally { setSavingConsent(false) }
  }

  async function download() {
    setExporting(true)
    try {
      const saved = await exportProfile()
      const draft = modules.c02?.value?.draft
      const file = {
        ...saved,
        research_modules: {
          skill_assessment: modules.c01?.value?.details || null,
          personality_analysis: draft ? { questionnaire: draft.questionnaire || null, scenarios: draft.sjt || null, writing: draft.writing || null } : null,
          career_prediction: modules.c03?.value?.all || null,
          learning_roadmap: modules.c04?.value?.record || null,
        },
      }
      const url = URL.createObjectURL(new Blob([JSON.stringify(file, null, 2)], { type: 'application/json' }))
      const link = Object.assign(document.createElement('a'), { href: url, download: `careernova-my-data-${new Date().toISOString().slice(0, 10)}.json` })
      document.body.append(link); link.click(); link.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      toast('Your data has been downloaded.')
    } catch (error) { toast(error.message, 'error') }
    finally { setExporting(false) }
  }

  const status = consent.research_use === true ? `You agreed on ${formatDate(consent.given_at)}.`
    : consent.research_use === false ? `You withdrew consent on ${formatDate(consent.updated_at)}. Your data is not used for research analysis.`
      : 'You have not given research consent yet. Your data is not used for research analysis.'

  return <div className="pf-stack">
    <section className="card pf-card" aria-labelledby="pf-consent">
      <header className="card-head"><div><h3 id="pf-consent">Research consent</h3><p>CareerNova is a university research project (J26-IT-385).</p></div>
        <span className={`pf-status ${consent.research_use ? 'is-done' : 'is-ready'}`}>{consent.research_use ? 'Consent given' : consent.research_use === false ? 'Withdrawn' : 'Not given'}</span></header>
      <div className="pf-switch-row">
        <div><strong id="pf-consent-label">Allow my anonymised data to be used for research analysis</strong><p className="pf-muted" id="pf-consent-status">{status}</p></div>
        <button type="button" role="switch" className={`pf-switch ${consent.research_use ? 'is-on' : ''}`} aria-checked={Boolean(consent.research_use)}
          aria-labelledby="pf-consent-label" aria-describedby="pf-consent-status" onClick={toggle} disabled={savingConsent}><i /></button>
      </div>
      <p className="pf-muted">You can change this at any time. Turning it off stops future use; it does not affect how the app works for you.</p>
    </section>

    <section className="card pf-card" aria-labelledby="pf-stored">
      <header className="card-head"><div><h3 id="pf-stored">What we store and why</h3></div></header>
      <ul className="pf-plain">
        <li><strong>Your account:</strong> name, email and a securely hashed password (or your Google sign-in), so you can log in.</li>
        <li><strong>Your profile details:</strong> what you enter on this page, to show your goals and preferences in one place.</li>
        <li><strong>Module results:</strong> skills read from your CV, career matches and your roadmap, linked to an anonymous assessment ID for this browser session. Personality answers stay in your browser session.</li>
        <li><strong>Not stored:</strong> your CV file. Only the skills read from it are kept.</li>
      </ul>
    </section>

    <section className="card pf-card" aria-labelledby="pf-your-data">
      <header className="card-head"><div><h3 id="pf-your-data">Your data</h3></div></header>
      <div className="pf-data-actions">
        <div><strong>Download my data</strong><p className="pf-muted">A JSON file with your account, profile, consent and module results.</p></div>
        <button type="button" className="button-secondary" onClick={download} disabled={exporting}><Icon name="document" size={15} />{exporting ? 'Preparing…' : 'Download my data'}</button>
      </div>
      <div className="pf-data-actions pf-danger-zone">
        <div><strong>Delete my account and data</strong><p className="pf-muted">Permanently removes your account and profile. This cannot be undone.</p></div>
        <button type="button" className="pf-danger" onClick={() => setConfirming(true)}>Delete account</button>
      </div>
    </section>

    {confirming && <DeleteDialog account={account} theme={theme} onClose={() => setConfirming(false)} toast={toast} />}
  </div>
}

function DeleteDialog({ account, theme, onClose, toast }) {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [typed, setTyped] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function confirm(event) {
    event.preventDefault()
    if (typed !== 'DELETE') return
    setBusy(true); setError('')
    try {
      await deleteAccount()
      for (const key of MODULE_KEYS) { try { sessionStorage.removeItem(key) } catch { /* storage unavailable */ } }
      try { await logout() } catch { /* the session is already gone */ }
      navigate('/login', { replace: true })
    } catch (err) {
      setError(err.message); setBusy(false)
      toast(err.message, 'error')
    }
  }

  return <Modal theme={theme} title="Delete your account and data?" onClose={busy ? () => {} : onClose} description={<>
    <p>This permanently deletes your CareerNova account, profile details, photo and research consent record, and signs you out.</p>
    <p>Your module results are linked to an anonymous assessment ID for this browser session; that link is removed from this browser.</p>
    {account.provider === 'google' && <p>Your Google sign-in itself is managed by Google and our sign-in provider; signing in again would start a new, empty profile.</p>}
  </>}>
    <form onSubmit={confirm} className="pf-delete-form">
      <label htmlFor="pf-delete-confirm">Type <strong>DELETE</strong> to confirm</label>
      <input id="pf-delete-confirm" value={typed} onChange={event => setTyped(event.target.value)} autoComplete="off" spellCheck="false" />
      {error && <p className="pf-error" role="alert">{error}</p>}
      <div className="pf-form-actions">
        <button type="button" className="button-secondary" onClick={onClose} disabled={busy}>Cancel</button>
        <button type="submit" className="pf-danger" disabled={typed !== 'DELETE' || busy}>{busy ? 'Deleting…' : 'Delete permanently'}</button>
      </div>
    </form>
  </Modal>
}
