// Avatar button with a small profile menu. Log out stays a separate, always-visible button.
import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import ShellIcon from './ShellIcons.jsx'
import { useProfilePhoto } from './profilePhoto.js'
import { THEME_MODES, setThemeMode, useThemeState } from './theme.js'

const MODE_LABELS = { light: 'Light', dark: 'Dark', system: 'System' }

const initials = name => name?.split(/\s+/).filter(Boolean).map(part => part[0]).slice(0, 2).join('').toUpperCase() || 'CN'

export default function AccountMenu({ user, onSearch }) {
  const [open, setOpen] = useState(false)
  const root = useRef(null)
  const button = useRef(null)
  const menuId = useId()
  // Uploaded profile photo first, then the Google account photo, then initials.
  const uploaded = useProfilePhoto(user)
  const photo = uploaded || user?.avatar_url || null
  const [broken, setBroken] = useState(null)
  const { mode } = useThemeState()

  useEffect(() => {
    if (!open) return undefined
    const onPointer = event => { if (!root.current?.contains(event.target)) setOpen(false) }
    const onKey = event => { if (event.key === 'Escape') { setOpen(false); button.current?.focus() } }
    document.addEventListener('pointerdown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('pointerdown', onPointer); document.removeEventListener('keydown', onKey) }
  }, [open])

  return <div className="account-menu" ref={root}>
    <button ref={button} type="button" className="account-trigger" aria-haspopup="true" aria-expanded={open} aria-controls={menuId} onClick={() => setOpen(value => !value)}>
      <span className="avatar" aria-label={user?.full_name} title={user?.full_name}>{photo && broken !== photo
        ? <img src={photo} alt={user.full_name} referrerPolicy="no-referrer" onError={() => setBroken(photo)} />
        : initials(user?.full_name)}</span>
      <span className="auth-account-profile" aria-hidden="true"><strong>{user?.full_name}</strong><small>{user?.email}</small></span>
      <span className="account-chevron" aria-hidden="true"><ShellIcon name="chevron" size={14} /></span>
    </button>
    {open && <div id={menuId} className="account-popover">
      <Link to="/profile" className="account-popover-head" onClick={() => setOpen(false)} aria-label={`My profile: ${user?.full_name || ''}`}><span className="account-popover-icon"><ShellIcon name="user" size={16} /></span><span><strong>{user?.full_name}</strong><small>{user?.email}</small></span></Link>
      <Link to="/profile" onClick={() => setOpen(false)}>My profile</Link>
      <Link to="/component01" onClick={() => setOpen(false)}>Your skill profile <small>01</small></Link>
      <Link to="/component04" onClick={() => setOpen(false)}>Your learning roadmap <small>04</small></Link>
      <button type="button" onClick={() => { setOpen(false); onSearch() }}>Search modules and sections</button>
      <div className="account-theme">
        <span id={`${menuId}-theme`}>Theme</span>
        <div role="radiogroup" aria-labelledby={`${menuId}-theme`}>{THEME_MODES.map(value => <button key={value} type="button" role="radio"
          aria-checked={mode === value} className={mode === value ? 'is-active' : ''} onClick={() => setThemeMode(value)}>{MODE_LABELS[value]}</button>)}</div>
      </div>
    </div>}
  </div>
}
