const paths = {
  spark: 'm12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4L12 3Z',
  grid: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  skill: 'm8 5-6 7 6 7 M16 5l6 7-6 7 M14 3l-4 18',
  personality: 'M9 18v3h6v-3 M9 18c-1-3-4-4-4-8a7 7 0 0 1 14 0c0 4-3 5-4 8H9Z M9 10h6 M12 7v6',
  career: 'M4 7h16v14H4z M8 7V3h8v4 M4 12h16 M10 12v3h4v-3',
  roadmap: 'M5 3v14a4 4 0 0 0 4 4h10 M5 3h5v5H5 M14 9h5v5h-5 M9 21v-7h5 M19 19l2 2-2 2',
  pulse: 'M2 12h5l3-8 4 16 3-8h5',
  arrow: 'M5 12h14 M13 6l6 6-6 6',
  menu: 'M4 6h16 M4 12h16 M4 18h16',
  close: 'm6 6 12 12 M6 18 18 6',
  check: 'm5 12 4 4 10-10',
}
export default function Icon({ name = 'spark', size = 20 }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.spark} /></svg>
}
