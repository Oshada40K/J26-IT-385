// Shared application shell; existing routes are preserved.
import { Suspense, lazy, useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import Sidebar from './components/Sidebar.jsx'
import PageTransition from './components/PageTransition.jsx'
import Home from './pages/Home.jsx'
import SkillProfile from './pages/component01/SkillProfile.jsx'
import PersonalityProfile from './pages/component02/PersonalityProfile.jsx'
import CareerRecommendation from './pages/component03/CareerRecommendation.jsx'
import LearningRoadmap from './pages/component04/LearningRoadmap.jsx'
import ApiTest from './pages/ApiTest.jsx'
import { AuthProvider, RequireAuth } from './auth/AuthContext.jsx'
// Auth pages load as their own chunk (with Motion's animation features), so the workspace bundle is unchanged.
const AuthLayout = lazy(() => import('./pages/auth/AuthLayout.jsx'))
const AuthPage = lazy(() => import('./pages/auth/AuthPage.jsx'))
const authFallback = <div className="auth-status" role="status">Opening CareerNova…</div>
import AuthCallback from './pages/auth/AuthCallback.jsx'
import { SkeletonDashboard } from './components/loading/index.js'
const Profile = lazy(() => import('./pages/profile/Profile.jsx')) // loaded only when /profile opens
export default function App() {
  return <AuthProvider><Routes>
    <Route path="/auth/callback" element={<AuthCallback />} />
    {/* One layout keeps the animated brand panel in place while the form slides between pages. */}
    <Route element={<Suspense fallback={authFallback}><AuthLayout /></Suspense>}>
      <Route path="/login" element={<AuthPage key="login" mode="login" />} />
      <Route path="/register" element={<AuthPage key="register" mode="register" />} />
      <Route path="/forgot-password" element={<AuthPage key="forgot" mode="forgot" />} />
      <Route path="/reset-password" element={<AuthPage key="reset" mode="reset" />} />
    </Route>
    <Route path="/*" element={<RequireAuth><Dashboard /></RequireAuth>} />
  </Routes></AuthProvider>
}
function Dashboard() {
  const [menuOpen, setMenuOpen] = useState(false)
  return <div className="app" onKeyDown={event => { if (event.key === 'Escape') setMenuOpen(false) }}><a href="#main-content" className="skip-link">Skip to content</a><Sidebar open={menuOpen} onNavigate={() => setMenuOpen(false)} />{menuOpen && <button className="sidebar-backdrop" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}<div className="main-shell"><Navbar menuOpen={menuOpen} onMenuToggle={() => setMenuOpen(v => !v)} /><main id="main-content" className="content"><PageTransition>{location => <Routes location={location}><Route path="/" element={<Home />} /><Route path="/component01" element={<SkillProfile />} /><Route path="/component02" element={<PersonalityProfile />} /><Route path="/component03" element={<CareerRecommendation />} /><Route path="/component04" element={<LearningRoadmap />} /><Route path="/profile" element={<Suspense fallback={<SkeletonDashboard label="Loading your profile" />}><Profile /></Suspense>} /><Route path="/api-test" element={<ApiTest />} /></Routes>}</PageTransition></main><footer className="app-footer"><span>CareerNova <span className="muted"> / Career intelligence, made personal.</span></span><span>J26-IT-385</span></footer></div></div>
}
