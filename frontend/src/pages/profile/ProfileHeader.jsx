// Header card: photo, name, email, university, member since, completeness ring and Edit button.
import { useRef, useState } from 'react'
import Icon from '../../components/Icon.jsx'
import { initials, photoProblem } from './profileModel.js'
import { Ring, formatDate } from './profileUi.jsx'

export default function ProfileHeader({ data, photo, fallbackPhoto, complete, onEdit, onPhoto, onRemovePhoto }) {
  const input = useRef(null)
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState('')
  const { account, profile } = data
  const role = [profile.degree, profile.university].filter(Boolean).join(' · ')
  const shown = photo || fallbackPhoto
  const memberSince = formatDate(account.member_since)

  async function choose(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    const reason = photoProblem(file)
    setProblem(reason)
    if (reason) return
    setBusy(true)
    try { await onPhoto(file) } finally { setBusy(false) }
  }

  return <section className="card pf-header reveal is-in" aria-labelledby="pf-name">
    <div className="pf-identity reveal-item">
      <div className="pf-avatar-wrap">
        <span className={`pf-avatar ${busy ? 'is-busy' : ''}`}>{shown
          ? <img src={shown} alt="" referrerPolicy="no-referrer" />
          : <span aria-hidden="true">{initials(account.full_name)}</span>}</span>
        <button type="button" className="pf-avatar-edit" onClick={() => input.current?.click()} disabled={busy}
          aria-label={photo ? 'Change profile photo' : 'Upload a profile photo'} title="JPG or PNG, up to 2 MB">
          <Icon name="upload" size={14} />
        </button>
        <input ref={input} type="file" accept="image/jpeg,image/png" hidden onChange={choose} />
      </div>
      <div className="pf-identity-text">
        <p className="pf-eyebrow">My profile</p>
        <h1 id="pf-name">{account.full_name}</h1>
        <p className="pf-email">{account.email}</p>
        <p className="pf-role">{role || <span className="pf-muted">University and degree not added yet</span>}</p>
        <p className="pf-meta">
          {memberSince ? <span>Member since {memberSince}</span>
            : <span title="This account was created before sign-up dates were recorded.">Member since: not recorded</span>}
          {account.provider === 'google' && <span className="pill pill-neutral">Signed in with Google</span>}
        </p>
        <div className="pf-photo-actions">
          <button type="button" className="pf-link" onClick={() => input.current?.click()} disabled={busy}>{busy ? 'Uploading…' : photo ? 'Change photo' : 'Upload photo'}</button>
          {photo && <button type="button" className="pf-link" onClick={onRemovePhoto} disabled={busy}>Remove photo</button>}
          <span className="pf-muted">JPG or PNG, up to 2 MB</span>
        </div>
        {problem && <p className="pf-error" role="alert">{problem}</p>}
      </div>
    </div>
    <div className="pf-complete reveal-item">
      <Ring percent={complete.percent} />
      <div>
        <strong>{complete.percent === 100 ? 'Your profile is complete' : 'Complete your profile'}</strong>
        <p className="pf-muted">{complete.done} of {complete.total} done: your details plus the four research modules.</p>
        {complete.missing.length > 0 && <ul className="pf-missing">{complete.missing.slice(0, 3).map(item => <li key={item.key}>{item.label}</li>)}</ul>}
        <button type="button" className="button pf-button-sm" onClick={onEdit}><Icon name="document" size={15} />Edit profile</button>
      </div>
    </div>
  </section>
}
