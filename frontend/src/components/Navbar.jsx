import { useLocation } from 'react-router-dom'
import Icon from './Icon.jsx'
const titles = { '/': 'Workspace overview', '/component01': 'Skill assessment', '/component02': 'Personality analysis', '/component03': 'Career prediction', '/component04': 'Learning roadmap', '/api-test': 'API integration' }
export default function Navbar({ menuOpen, onMenuToggle }) {
  const { pathname } = useLocation()
  return <header className="navbar">
    <div className="navbar-context"><button className="menu-toggle button-secondary" onClick={onMenuToggle} aria-expanded={menuOpen} aria-controls="main-navigation" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'}><Icon name={menuOpen ? 'close' : 'menu'} /></button><span className="navbar-breadcrumb">CareerNova <span>/</span> <strong>{titles[pathname] || 'Workspace'}</strong></span></div>
    <div className="navbar-right"><span className="research-badge">Research workspace</span><span className="avatar" aria-label="University research team">CN</span></div>
  </header>
}
