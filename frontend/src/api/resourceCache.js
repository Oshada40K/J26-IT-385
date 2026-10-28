// In-memory stale-while-revalidate cache for page data.
// Pages unmount on navigation; reading the last result from here lets them render it
// immediately on return instead of flashing a loader, while they refresh in the background.
// Identical requests that are already in flight are shared (e.g. React StrictMode, C03 and C04).
import { savedSession } from '../pages/component01/skillApi.js'

const store = new Map()
const inflight = new Map()
let generation = 0

export const hasCached = key => store.has(key)
export const peek = key => store.get(key)
export const prime = (key, data) => { store.set(key, data) }

// Cache key for data that belongs to the current CV candidate (shared by all components).
export const candidateKey = name => `${name}:${savedSession()?.candidate_id || 'none'}`

export function cached(key, fetcher) {
  if (inflight.has(key)) return inflight.get(key)
  const started = generation
  const request = Promise.resolve().then(fetcher)
    .then(data => { if (started === generation) store.set(key, data); return data })
    .finally(() => { if (inflight.get(key) === request) inflight.delete(key) })
  inflight.set(key, request)
  return request
}

// The stored result if there is one, otherwise a (shared) request. For data another page loads.
export const reuse = (key, fetcher) => store.has(key) ? Promise.resolve(store.get(key)) : cached(key, fetcher)

// Drops cached entries whose key starts with `prefix` (everything by default).
// Requests already in flight still resolve for their callers but are not stored.
export function invalidate(prefix = '') {
  generation += 1
  for (const map of [store, inflight]) for (const key of [...map.keys()]) if (key.startsWith(prefix)) map.delete(key)
}
