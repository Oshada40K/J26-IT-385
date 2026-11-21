// The signed-in user's uploaded profile photo, shared by the top bar and the profile page so a
// new photo shows everywhere at once. Loaded once per account; null when none is uploaded or
// the profile service is unavailable (callers then fall back to the Google photo or initials).
import { useEffect, useSyncExternalStore } from 'react'
import { getProfile, photoUrl } from '../../pages/profile/profileApi.js'

let current = { owner: null, url: null }
let pending = null
let pendingOwner = null
const listeners = new Set()

function setPhoto(owner, url) {
  if (current.url && current.url !== url) URL.revokeObjectURL(current.url)
  current = { owner, url }
  listeners.forEach(listener => listener())
}

// force: reload after an upload or removal on the profile page.
export function loadProfilePhoto(owner, { force = false } = {}) {
  if (!owner) { setPhoto(null, null); return Promise.resolve() }
  if (!force && current.owner === owner) return Promise.resolve()
  if (!force && pending && pendingOwner === owner) return pending
  pendingOwner = owner
  const request = (async () => {
    let url = null
    try {
      const data = await getProfile()
      if (data.avatar?.present) url = await photoUrl()
    } catch { url = null }
    if (pendingOwner !== owner) { if (url) URL.revokeObjectURL(url); return } // the account changed meanwhile
    setPhoto(owner, url)
  })().finally(() => { if (pending === request) pending = null })
  pending = request
  return request
}

const subscribe = listener => { listeners.add(listener); return () => listeners.delete(listener) }
const snapshot = () => current

export const photoOwner = user => user ? `${user.id}:${user.email}` : null

export function useProfilePhoto(user) {
  const owner = photoOwner(user)
  const state = useSyncExternalStore(subscribe, snapshot, snapshot)
  useEffect(() => { loadProfilePhoto(owner) }, [owner])
  return state.owner === owner ? state.url : null
}
