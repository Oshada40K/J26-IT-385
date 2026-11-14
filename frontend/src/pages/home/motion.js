// One motion system for the whole Home page. Only transform and opacity are animated.
export const EASE = [0.22, 1, 0.36, 1]
export const DURATION = { micro: 0.15, ui: 0.3, section: 0.6 }
export const STAGGER = 0.06
export const VIEWPORT = { once: true, amount: 0.2 }

// Section entrance: fade + 16px rise, children staggered 60ms.
export const sectionVariants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: DURATION.section, ease: EASE, staggerChildren: STAGGER } },
}
export const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: DURATION.section, ease: EASE } },
}
// Headline word-by-word reveal.
export const wordsVariants = { hidden: {}, show: { transition: { staggerChildren: 0.07, delayChildren: 0.1 } } }
export const wordVariants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: DURATION.section, ease: EASE } },
}
// Small UI changes (status text, cards swapping).
export const swapVariants = {
  initial: { opacity: 0, y: 6 },
  enter: { opacity: 1, y: 0, transition: { duration: DURATION.ui, ease: EASE } },
  exit: { opacity: 0, y: -6, transition: { duration: DURATION.micro } },
}
// CSS custom properties with the same tokens, for CSS-driven transitions.
export const cssTokens = { '--ease-out': 'cubic-bezier(.22, 1, .36, 1)', '--dur-micro': '150ms', '--dur-ui': '300ms', '--dur-section': '600ms' }
