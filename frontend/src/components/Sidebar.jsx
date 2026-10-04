import { NavLink } from 'react-router-dom'
import Icon from './Icon.jsx'
const links = [
  { to: '/', label: 'Overview', icon: 'grid' },
  { to: '/component01', label: 'Skill assessment', icon: 'skill', number: '01' },
  { to: '/component02', label: 'Personality analysis', icon: 'personality', number: '02' },
  { to: '/component03', label: 'Career prediction', icon: 'career', number: '03' },
  { to: '/component04', label: 'Learning roadmap', icon: 'roadmap', number: '04' },
  { to: '/api-test', label: 'API integration', icon: 'pulse' },
]
export default function Sidebar({ open, onNavigate }) {
  return <aside className={`sidebar ${open ? 'is-open' : ''}`}>
    <NavLink to="/" className="brand" onClick={onNavigate}><span className="brand-mark"><Icon size={25} /></span><span>CareerNova<small>CAREER INTELLIGENCE</small></span></NavLink>
    <div className="nav-label">YOUR WORKSPACE</div>
    <nav id="main-navigation" aria-label="Main navigation">{links.map(link => <NavLink key={link.to} to={link.to} end onClick={onNavigate}><Icon name={link.icon} /><span>{link.label}</span>{link.number && <small>{link.number}</small>}</NavLink>)}</nav>
    <div className="sidebar-bottom"><div className="sidebar-note"><Icon /><strong>Intelligence with clarity</strong><p>Skills. Personality. Direction.<br />One connected career journey.</p></div><div className="project-label">J26-IT-385 <span>UNIVERSITY RESEARCH</span></div></div>
  </aside>
}
