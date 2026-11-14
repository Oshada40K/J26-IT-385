// Light/dark preference for the Home page. Components 01-04 have no dark styles, so the
// theme is applied only while Home is mounted (see useHomeTheme) and the toggle shows only there.
import { useEffect, useSyncExternalStore } from 'react'

const KEY = 'careernova-home-theme'
const listeners = new Set()

function read() {
  try { return localStorage.getItem(KEY) === 'dark' ? 'dark' : 'light' }
  catch { return 'light' }
}

let theme = read()

export function getTheme() { return theme }

export function setTheme(next) {
  theme = next === 'dark' ? 'dark' : 'light'
  try { localStorage.setItem(KEY, theme) } catch { /* private mode: the choice lasts this visit */ }
  listeners.forEach(listener => listener())
}

function subscribe(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useTheme() {
  return useSyncExternalStore(subscribe, getTheme, getTheme)
}

// Called by the Home page: paints the canvas, navbar and footer while Home is on screen.
export function useHomeTheme() {
  const current = useTheme()
  useEffect(() => {
    const root = document.documentElement
    root.dataset.homeTheme = current
    return () => { delete root.dataset.homeTheme }
  }, [current])
  return current
}
