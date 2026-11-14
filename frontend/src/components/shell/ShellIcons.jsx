// Small icons used only by the app shell (kept here so the shared Icon set stays unchanged).
const paths = {
  search: 'M11 4a7 7 0 1 1 0 14 7 7 0 0 1 0-14Z M20 20l-3.5-3.5',
  sun: 'M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8Z M12 2v2 M12 20v2 M4.9 4.9l1.4 1.4 M17.7 17.7l1.4 1.4 M2 12h2 M20 12h2 M4.9 19.1l1.4-1.4 M17.7 6.3l1.4-1.4',
  moon: 'M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z',
  chevron: 'm6 9 6 6 6-6',
  enter: 'M9 10l-5 5 5 5 M20 4v7a4 4 0 0 1-4 4H4',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z M4 21a8 8 0 0 1 16 0',
}

export default function ShellIcon({ name, size = 18 }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>
}
