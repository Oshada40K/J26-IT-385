// App-wide colour theme: Light, Dark or System (default). The choice is saved in localStorage
// and applied to <html> as data-theme="light|dark" plus a `dark` class. index.html applies it
// before the first paint (no white flash); this module keeps it in sync afterwards.
import { useEffect, useSyncExternalStore } from 'react'
import '../../theme-dark.css'

const KEY = 'careernova-theme'
const LEGACY_KEY = 'careernova-home-theme' // the earlier Home-only toggle
export const THEME_MODES = ['light', 'dark', 'system']
const listeners = new Set()
const media = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null

function readMode() {
  try {
    const saved = localStorage.getItem(KEY)
    if (THEME_MODES.includes(saved)) return saved
    return localStorage.getItem(LEGACY_KEY) === 'dark' ? 'dark' : 'system'
  } catch { return 'system' }
}

const resolve = value => value === 'system' ? (media?.matches ? 'dark' : 'light') : value

let mode = readMode()
let state = { mode, theme: resolve(mode) }

function apply(animate) {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  if (animate) {
    // A short colour cross-fade while switching (see .theme-switching in index.css).
    root.classList.add('theme-switching')
    clearTimeout(apply.timer)
    apply.timer = setTimeout(() => root.classList.remove('theme-switching'), 260)
  }
  root.dataset.theme = state.theme
  root.classList.toggle('dark', state.theme === 'dark')
  root.style.colorScheme = state.theme
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', state.theme === 'dark' ? '#0B1020' : '#F6F7FB')
}

function update(animate) {
  const next = { mode, theme: resolve(mode) }
  if (next.mode === state.mode && next.theme === state.theme) return
  state = next
  apply(animate)
  listeners.forEach(listener => listener())
}

export function setThemeMode(next) {
  mode = THEME_MODES.includes(next) ? next : 'system'
  try { localStorage.setItem(KEY, mode); localStorage.removeItem(LEGACY_KEY) } catch { /* private mode: lasts this visit */ }
  update(true)
}

// Light <-> dark, as an explicit choice (used by the toggle buttons).
export function toggleTheme() { setThemeMode(state.theme === 'dark' ? 'light' : 'dark') }
export const setTheme = value => setThemeMode(value) // earlier name, kept for callers
export const getTheme = () => state.theme

function subscribe(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
const snapshot = () => state

export function useThemeState() { return useSyncExternalStore(subscribe, snapshot, snapshot) }
// The resolved theme, 'light' or 'dark'.
export function useTheme() { return useThemeState().theme }
// Home and Profile pass this to their .cn-home root (their tokens switch on data-theme).
export const useHomeTheme = useTheme

// Follows the operating-system setting while the mode is System, and syncs other tabs.
export function ThemeProvider({ children }) {
  useEffect(() => {
    apply(false)
    const onSystem = () => { if (mode === 'system') update(true) }
    const onStorage = event => { if (event.key === KEY) { mode = readMode(); update(true) } }
    media?.addEventListener?.('change', onSystem)
    window.addEventListener('storage', onStorage)
    return () => { media?.removeEventListener?.('change', onSystem); window.removeEventListener('storage', onStorage) }
  }, [])
  return children
}
