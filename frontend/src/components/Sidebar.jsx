import { useLayoutEffect, useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import Icon from './Icon.jsx'
import { useJourney } from '../pages/home/journey.js'
const links = [
  { to: '/', label: 'Home', icon: 'home' },
  { to: '/component01', label: 'Skill assessment', icon: 'skill', number: '01', step: 'c01' },
  { to: '/component02', label: 'Personality analysis', icon: 'personality', number: '02', step: 'c02' },
  { to: '/component03', label: 'Career prediction', icon: 'career', number: '03', step: 'c03' },
  { to: '/component04', label: 'Learning roadmap', icon: 'roadmap', number: '04', step: 'c04' },
  { to: '/api-test', label: 'API integration', icon: 'pulse' },
]
export default function Sidebar({ open, onNavigate }) {
  const { pathname } = useLocation()
  const { statuses } = useJourney()
  const nav = useRef(null)
  const [indicator, setIndicator] = useState(null)
  // One highlight slides to the active link instead of each link painting its own.
  useLayoutEffect(() => {
    const measure = () => {
      const active = nav.current?.querySelector('a.active')
      setIndicator(active ? { top: active.offsetTop, height: active.offsetHeight } : null)
    }
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [pathname])
  return <aside className={`sidebar ${open ? 'is-open' : ''}`}>
    <NavLink to="/" className="brand" onClick={onNavigate}><span className="brand-mark"><Icon size={25} /></span><span>CareerNova<small>CAREER INTELLIGENCE</small></span></NavLink>
    <div className="nav-label">YOUR WORKSPACE</div>
    <nav id="main-navigation" aria-label="Main navigation" ref={nav}>
      {indicator && <span className="nav-indicator" aria-hidden="true" style={{ transform: `translateY(${indicator.top}px)`, height: indicator.height }} />}
      {links.map(link => {
        const done = link.step && statuses[link.step] === 'done'
        return <NavLink key={link.to} to={link.to} end onClick={onNavigate} data-label={link.label}><Icon name={link.icon} /><span>{link.label}{done && <span className="sr-only"> (completed)</span>}</span>{link.number && <small className={done ? 'is-done' : ''}>{done ? <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m5 12 4 4 10-10" /></svg> : link.number}</small>}</NavLink>
      })}
    </nav>
    <div className="sidebar-bottom"><div className="sidebar-note"><Icon /><strong>Intelligence with clarity</strong><p>Skills. Personality. Direction.<br />One connected career journey.</p></div><div className="project-label">J26-IT-385 <span>UNIVERSITY RESEARCH</span></div></div>
  </aside>
}
