// SHARED FILE - controlled by the group leader.
import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Home' },
  { to: '/component01', label: 'Component 01' },
  { to: '/component02', label: 'Component 02' },
  { to: '/component03', label: 'Component 03' },
  { to: '/component04', label: 'Component 04' },
  { to: '/api-test', label: 'API Test' },
]

export default function Sidebar() {
  return (
    <nav className="sidebar">
      {links.map((link) => (
        <NavLink key={link.to} to={link.to} end>
          {link.label}
        </NavLink>
      ))}
    </nav>
  )
}
