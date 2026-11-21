// Light/dark toggle used in the top bar and on the auth pages. The sun and moon rotate and
// scale as they swap (shell.css, .theme-toggle). Choosing here sets an explicit Light or Dark;
// System is available in the account menu.
import ShellIcon from './ShellIcons.jsx'
import { toggleTheme, useTheme } from './theme.js'

export default function ThemeToggle({ className = '' }) {
  const theme = useTheme()
  const next = theme === 'dark' ? 'light' : 'dark'
  return <button type="button" className={`theme-toggle is-${theme} ${className}`} onClick={toggleTheme}
    aria-label={`Switch to ${next} mode`} title={`${next === 'dark' ? 'Dark' : 'Light'} mode`}>
    <span className="theme-sun"><ShellIcon name="sun" size={17} /></span>
    <span className="theme-moon"><ShellIcon name="moon" size={17} /></span>
  </button>
}
