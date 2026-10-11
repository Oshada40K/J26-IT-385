import { useLocation } from 'react-router-dom'
import Icon from './Icon.jsx'
import { useState } from 'react'
import { useAuth } from '../auth/AuthContext.jsx'
const titles = { '/': 'Home', '/component01': 'Skill assessment', '/component02': 'Personality analysis', '/component03': 'Career prediction', '/component04': 'Learning roadmap', '/api-test': 'API integration' }
export default function Navbar({ menuOpen, onMenuToggle }) {
  const { pathname } = useLocation()
  const { user, logout } = useAuth()
  const [loggingOut, setLoggingOut] = useState(false)
  const [error, setError] = useState('')
  async function handleLogout() {
    setLoggingOut(true); setError('')
    try { await logout() } catch (err) { setError(err.message) }
    finally { setLoggingOut(false) }
  }
  return <header className="navbar">
    <div className="navbar-context"><button className="menu-toggle button-secondary" onClick={onMenuToggle} aria-expanded={menuOpen} aria-controls="main-navigation" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'}><Icon name={menuOpen ? 'close' : 'menu'} /></button><span className="navbar-breadcrumb">CareerNova <span>/</span> <strong>{titles[pathname] || 'Workspace'}</strong></span></div>
    <div className="navbar-right"><span className="research-badge">Research workspace</span><div className="auth-account-actions"><span className="avatar" aria-label={user?.full_name} title={user?.full_name}>{user?.avatar_url ? <img src={user.avatar_url} alt={user.full_name} referrerPolicy="no-referrer" onError={event => { event.currentTarget.style.display = 'none' }} /> : user?.full_name?.split(/\s+/).map(part => part[0]).slice(0, 2).join('').toUpperCase() || 'CN'}</span><span className="auth-account-profile"><strong>{user?.full_name}</strong><small>{user?.email}</small></span>{error && <span role="alert" className="auth-logout-error">{error}</span>}<button className="button-secondary" onClick={handleLogout} disabled={loggingOut}>{loggingOut ? 'Logging out…' : 'Log out'}</button></div></div>
  </header>
}
