// SHARED FILE - controlled by the group leader.
// Ask the group leader before adding or changing routes.
import { Link, Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import Sidebar from './components/Sidebar.jsx'
import SkillProfile from './pages/component01/SkillProfile.jsx'
import PersonalityProfile from './pages/component02/PersonalityProfile.jsx'
import CareerRecommendation from './pages/component03/CareerRecommendation.jsx'
import LearningRoadmap from './pages/component04/LearningRoadmap.jsx'
import ApiTest from './pages/ApiTest.jsx'

const components = [
  { path: '/component01', title: 'Component 01', name: 'Technical Skill Profile', owner: 'Tharindi' },
  { path: '/component02', title: 'Component 02', name: 'Personality Profile', owner: 'Nethmi' },
  { path: '/component03', title: 'Component 03', name: 'Explainable Career Recommendation', owner: 'Oshada' },
  { path: '/component04', title: 'Component 04', name: 'Learning Roadmap & Skill Gap', owner: 'Dewmi' },
]

function Home() {
  return (
    <div>
      <h1>AI-Based Smart Career Path Recommendation System</h1>
      <div className="cards">
        {components.map((c) => (
          <Link key={c.path} to={c.path} className="card">
            <h3>{c.title}</h3>
            <p>{c.name}</p>
            <small>Owner: {c.owner}</small>
          </Link>
        ))}
      </div>
    </div>
  )
}

export default function App() {
  return (
    <div className="app">
      <Navbar />
      <div className="layout">
        <Sidebar />
        <main className="content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/component01" element={<SkillProfile />} />
            <Route path="/component02" element={<PersonalityProfile />} />
            <Route path="/component03" element={<CareerRecommendation />} />
            <Route path="/component04" element={<LearningRoadmap />} />
            <Route path="/api-test" element={<ApiTest />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
