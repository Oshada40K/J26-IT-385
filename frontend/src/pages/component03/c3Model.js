// Pure presentation helpers for Component 03 (no browser APIs, so they run under node --test).
// They only reformat values the career APIs return; nothing here changes a score.

// "42–42" reads as broken: when both ends round to the same whole number, say it is stable.
export function rangeLabel(low, high) {
  const a = Math.round(low), b = Math.round(high)
  return a === b ? `Stable at ~${a}` : `${a}–${b}`
}

// A band narrower than this many points (on the 0–100 scale) is drawn as a solid dot.
export const NARROW_BAND = 0.6
export const isNarrow = (low, high) => high - low < NARROW_BAND

const WORD = /[a-z]{4,}/g
const stem = word => word.slice(0, 6)

// Links a SHAP factor to the reasons that talk about it: the reason contains the whole label,
// or shares at least two of its significant words (first six letters, so "categories" ~ "category").
export function reasonMatches(label, reasons) {
  const lower = label.toLowerCase()
  const words = [...new Set((lower.match(WORD) || []).filter(w => !['this', 'that', 'with', 'used', 'your'].includes(w)).map(stem))]
  return reasons.map((reason, index) => {
    const text = reason.toLowerCase()
    if (text.includes(lower)) return index
    const found = words.filter(word => (text.match(WORD) || []).some(w => stem(w) === word)).length
    return found >= Math.min(2, words.length) && words.length > 1 ? index : -1
  }).filter(index => index >= 0)
}

// The technical-skills factor is the one the matched skills feed.
export const isTechnicalFactor = label => /technical skills|technolog/i.test(label)

// Gap to the #1 score, at the precision the API reports (2 decimals).
export function gapToTop(score, topScore) {
  const gap = Math.round((topScore - score) * 100) / 100
  return { gap, tied: gap === 0, label: gap === 0 ? 'Tied for #1' : `−${gap.toFixed(2)} pts` }
}

// "Zoom to differences": maps scores onto a min–max axis with a little padding either side.
export function zoomAxis(scores) {
  const min = Math.min(...scores), max = Math.max(...scores)
  const pad = Math.max((max - min) * 0.25, 0.05)
  const lo = Math.max(0, min - pad), hi = Math.min(100, max + pad)
  return { lo, hi, position: score => ((score - lo) / (hi - lo)) * 100 }
}

export const pct = value => Math.round(value * 100)

// Evidence confidence counts as shares for the segmented bar.
export function confidenceShares(counts) {
  const total = (counts.high || 0) + (counts.medium || 0) + (counts.low || 0)
  if (!total) return []
  return ['high', 'medium', 'low'].map(level => ({ level, count: counts[level] || 0, share: (counts[level] || 0) / total }))
}

// What-if gains by technology, so "Skills to learn" chips can show the real model delta.
export function gainsByTechnology(actions = []) {
  const map = {}
  for (const action of actions) if (action.action === 'learn' && action.score_gain > 0) map[action.technology] = action
  return map
}
