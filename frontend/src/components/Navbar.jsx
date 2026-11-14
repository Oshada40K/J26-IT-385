import { useLocation } from 'react-router-dom'
import Icon from './Icon.jsx'
import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext.jsx'
import AccountMenu from './shell/AccountMenu.jsx'
import CommandPalette from './shell/CommandPalette.jsx'
import ShellIcon from './shell/ShellIcons.jsx'
import { shortcutLabel } from './shell/paletteItems.js'
import ThemeToggle from './shell/ThemeToggle.jsx'
import './shell/shell.css'
const titles = { '/': 'Home', '/component01': 'Skill assessment', '/component02': 'Personality analysis', '/component03': 'Career prediction', '/component04': 'Learning roadmap', '/api-test': 'API integration', '/profile': 'My profile' }
export default function Navbar({ menuOpen, onMenuToggle }) {
  const { pathname } = useLocation()
  const { user, logout } = useAuth()
  const [loggingOut, setLoggingOut] = useState(false)
  const [error, setError] = useState('')
  const [scrolled, setScrolled] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 4)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  useEffect(() => {
    const onKey = event => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); setPaletteOpen(open => !open) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
  async function handleLogout() {
    setLoggingOut(true); setError('')
    try { await logout() } catch (err) { setError(err.message) }
    finally { setLoggingOut(false) }
  }
  const openPalette = () => setPaletteOpen(true)
  return <header className={`navbar ${scrolled ? 'is-scrolled' : ''}`}>
    <div className="navbar-context"><button className="menu-toggle button-secondary" onClick={onMenuToggle} aria-expanded={menuOpen} aria-controls="main-navigation" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'}><Icon name={menuOpen ? 'close' : 'menu'} /></button><span className="navbar-breadcrumb">CareerNova <span>/</span> <strong>{titles[pathname] || 'Workspace'}</strong></span></div>
    <div className="navbar-right">
      <button type="button" className="nav-search" onClick={openPalette} aria-keyshortcuts="Control+K Meta+K"><ShellIcon name="search" size={16} /><span className="nav-search-text">Search<span className="sr-only"> modules and sections</span></span><kbd aria-hidden="true">{shortcutLabel()}</kbd></button>
      <ThemeToggle />
      <button type="button" className="research-badge" onClick={openPalette}>Research workspace</button>
      <div className="auth-account-actions"><AccountMenu user={user} onSearch={openPalette} />{error && <span role="alert" className="auth-logout-error">{error}</span>}<button className="button-secondary" onClick={handleLogout} disabled={loggingOut}>{loggingOut ? 'Logging out…' : 'Log out'}</button></div>
    </div>
    {paletteOpen && <CommandPalette onClose={() => setPaletteOpen(false)} />}
  </header>
}
