// Shared application shell; existing routes are preserved.
import { useState } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import Sidebar from './components/Sidebar.jsx'
import Icon from './components/Icon.jsx'
import SkillProfile from './pages/component01/SkillProfile.jsx'
import PersonalityProfile from './pages/component02/PersonalityProfile.jsx'
import CareerRecommendation from './pages/component03/CareerRecommendation.jsx'
import LearningRoadmap from './pages/component04/LearningRoadmap.jsx'
import ApiTest from './pages/ApiTest.jsx'
const components = [
  { path: '/component01', number: '01', name: 'Skill assessment', description: 'Understand the technical strengths that shape your next opportunity.', owner: 'Tharindi', accent: 'skill', icon: 'skill', status: 'In development' },
  { path: '/component02', number: '02', name: 'Personality analysis', description: 'Explore the human strengths behind how you think, learn and collaborate.', owner: 'Nethmi', accent: 'personality', icon: 'personality', status: 'In development' },
  { path: '/component03', number: '03', name: 'Career prediction', description: 'Discover ranked career matches and the evidence behind each recommendation.', owner: 'Oshada', accent: 'career', icon: 'career', status: 'Prototype inference' },
  { path: '/component04', number: '04', name: 'Learning roadmap', description: 'Connect future skill gaps with a clear, personalized learning direction.', owner: 'Dewmi', accent: 'roadmap', icon: 'roadmap', status: 'In development' },
]
function Home() {
  return <div className="page dashboard">
    <div className="page-heading"><div><p className="eyebrow">YOUR NEXT CHAPTER</p><h1>A clearer path to your future.</h1><p className="page-description">Understand your strengths. Explore your possibilities. Build your direction.</p></div><span className="status status-neutral">Research prototype</span></div>
    <section className="intelligence-hero"><div className="hero-copy"><span className="hero-label"><Icon size={16} /> AI-POWERED CAREER INTELLIGENCE</span><h2>Your potential,<br />translated into possibility.</h2><p>From technical skills and personality to explainable career recommendations and a personalized learning journey.</p><Link to="/component03" className="button button-light">Explore career matches <Icon name="arrow" size={18} /></Link></div><div className="hero-visual" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="intelligence-core"><Icon size={42} /><span>CareerNova</span><small>CONNECTED INTELLIGENCE</small></div><span className="orbit-chip chip-skill"><Icon name="skill" /> Skills</span><span className="orbit-chip chip-personality"><Icon name="personality" /> Personality</span><span className="orbit-chip chip-career"><Icon name="career" /> Career</span><span className="orbit-chip chip-roadmap"><Icon name="roadmap" /> Growth</span></div></section>
    <div className="section-heading"><div><p className="eyebrow">FOUR PERSPECTIVES. ONE JOURNEY.</p><h2>Your career intelligence workspace</h2></div><span className="muted">Built around your potential</span></div>
    <div className="cards">{components.map(c => <Link key={c.path} to={c.path} className={`card component-card accent-${c.accent}`}><div className="component-card-top"><span className="component-icon"><Icon name={c.icon} size={23} /></span><span className="component-number">{c.number}</span></div><h3>{c.name}</h3><p>{c.description}</p><span className="component-stage">{c.status}</span><div className="component-card-footer"><small>Research lead: {c.owner}</small><Icon name="arrow" size={17} /></div></Link>)}</div>
    <section className="journey-panel card"><div className="section-heading"><div><p className="eyebrow">THE CAREERNOVA APPROACH</p><h2>More than a recommendation. A reason to move forward.</h2></div><span className="status status-ai"><Icon size={14} /> Explainable by design</span></div><div className="journey-steps">{components.map((c, i) => <div key={c.number} className={`journey-step accent-${c.accent}`}><span className="step-number">{c.number}</span><div><strong>{['Understand your skills', 'Discover your profile', 'Explore your matches', 'Plan your growth'][i]}</strong><p>{['Technical evidence', 'Personal strengths', 'Transparent AI reasoning', 'Personalized next steps'][i]}</p></div></div>)}</div><p className="prototype-note">AI-Based Smart Career Path Recommendation System &middot; University research project J26-IT-385. Current career scores are prototype evidence matches, not hiring probabilities.</p></section>
  </div>
}
export default function App() {
  const [menuOpen, setMenuOpen] = useState(false)
  return <div className="app" onKeyDown={event => { if (event.key === 'Escape') setMenuOpen(false) }}><a href="#main-content" className="skip-link">Skip to content</a><Sidebar open={menuOpen} onNavigate={() => setMenuOpen(false)} />{menuOpen && <button className="sidebar-backdrop" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}<div className="main-shell"><Navbar menuOpen={menuOpen} onMenuToggle={() => setMenuOpen(v => !v)} /><main id="main-content" className="content"><Routes><Route path="/" element={<Home />} /><Route path="/component01" element={<SkillProfile />} /><Route path="/component02" element={<PersonalityProfile />} /><Route path="/component03" element={<CareerRecommendation />} /><Route path="/component04" element={<LearningRoadmap />} /><Route path="/api-test" element={<ApiTest />} /></Routes></main><footer className="app-footer"><span>CareerNova <span className="muted"> / Career intelligence, made personal.</span></span><span>J26-IT-385</span></footer></div></div>
}
