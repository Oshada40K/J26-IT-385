// /profile: the signed-in user's profile, career journey summary, account security and privacy.
// Uses the Home design system (tokens, cards, motion) and the Home light/dark theme.
import { useCallback, useEffect, useId, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AnimatePresence, m } from 'motion/react'
import { useAuth } from '../../auth/AuthContext.jsx'
import { ErrorState } from '../../components/loading/index.js'
import { Bone } from '../../components/loading/Skeletons.jsx'
import { useHomeTheme } from '../../components/shell/theme.js'
import { loadProfilePhoto, photoOwner, useProfilePhoto } from '../../components/shell/profilePhoto.js'
import MotionRoot from '../home/MotionRoot.jsx'
import { refreshJourney, useJourney } from '../home/journey.js'
import { swapVariants } from '../home/motion.js'
import '../home/home.css'
import './profile.css'
import AccountTab from './AccountTab.jsx'
import EditDetailsTab from './EditDetailsTab.jsx'
import OverviewTab from './OverviewTab.jsx'
import PrivacyTab from './PrivacyTab.jsx'
import ProfileHeader from './ProfileHeader.jsx'
import { useModuleData } from './moduleData.js'
import { deletePhoto, getProfile, saveConsent, saveProfile, uploadPhoto } from './profileApi.js'
import { completeness } from './profileModel.js'
import { Tabs, Toasts, useToasts } from './profileUi.jsx'

const TABS = [
  { value: 'overview', label: 'Overview' },
  { value: 'edit', label: 'Edit details' },
  { value: 'account', label: 'Account' },
  { value: 'privacy', label: 'Privacy' },
]
const LEAVE_MESSAGE = 'You have unsaved changes to your details. Leave without saving?'

export default function Profile() {
  const theme = useHomeTheme()
  const { user, refresh } = useAuth()
  const journey = useJourney()
  const [modules] = useModuleData()
  const [params, setParams] = useSearchParams()
  const tab = TABS.some(item => item.value === params.get('tab')) ? params.get('tab') : 'overview'
  const [state, setState] = useState({ loading: true, data: null, error: '' })
  const photo = useProfilePhoto(user) // shared with the top bar
  const [dirty, setDirty] = useState(false)
  const { items, push, dismiss } = useToasts()
  const idPrefix = useId().replace(/:/g, '')

  const load = useCallback(async () => {
    setState(current => ({ ...current, loading: true, error: '' }))
    try { setState({ loading: false, data: await getProfile(), error: '' }) }
    catch (error) { setState({ loading: false, data: null, error: error.message }) }
  }, [])
  useEffect(() => { load(); refreshJourney() }, [load])

  // A new or removed photo reloads the shared copy, so the top bar updates too.
  const reloadPhoto = () => loadProfilePhoto(photoOwner(user), { force: true })

  // Unsaved details: warn on reload/close and on in-app links.
  useEffect(() => {
    if (!dirty) return undefined
    const onUnload = event => { event.preventDefault(); event.returnValue = '' }
    const onClick = event => {
      const link = event.target.closest?.('a[href]')
      if (!link || link.target === '_blank' || link.origin !== window.location.origin) return
      if (!window.confirm(LEAVE_MESSAGE)) { event.preventDefault(); event.stopPropagation() }
    }
    window.addEventListener('beforeunload', onUnload)
    document.addEventListener('click', onClick, true)
    return () => { window.removeEventListener('beforeunload', onUnload); document.removeEventListener('click', onClick, true) }
  }, [dirty])

  const goTo = useCallback(next => {
    if (next === tab) return
    if (dirty && tab === 'edit' && !window.confirm(LEAVE_MESSAGE)) return
    setParams(next === 'overview' ? {} : { tab: next }, { replace: true })
  }, [dirty, tab, setParams])

  const apply = data => setState(current => ({ ...current, data }))
  const fail = error => { push(error.message || 'Something went wrong. Please try again.', 'error'); throw error }

  const onSave = async body => {
    try {
      const data = await saveProfile(body)
      apply(data)
      push('Your details have been saved.')
      if (data.account.provider === 'password') refresh() // updates the name in the top bar
      return data.profile
    } catch (error) { return fail(error) }
  }
  const onPhoto = file => uploadPhoto(file).then(async data => { apply(data); await reloadPhoto(); push('Profile photo updated.') }).catch(error => push(error.message, 'error'))
  const onRemovePhoto = () => deletePhoto().then(async data => { apply(data); await reloadPhoto(); push('Profile photo removed.') }).catch(error => push(error.message, 'error'))
  const onConsent = value => saveConsent(value).then(data => {
    apply(data)
    push(value ? 'Thank you. Your research consent has been recorded.' : 'Research consent withdrawn.')
  }).catch(error => push(error.message, 'error'))

  const data = state.data
  return <MotionRoot><div className="page cn-home cn-profile" data-theme={theme}>
    {state.loading && !data ? <ProfileSkeleton />
      : state.error && !data ? <ErrorState title="We could not load your profile" message={state.error} onRetry={load} retrying={state.loading} />
        : <>
          <ProfileHeader data={data} photo={photo} fallbackPhoto={user?.avatar_url} onEdit={() => goTo('edit')} onPhoto={onPhoto} onRemovePhoto={onRemovePhoto}
            complete={completeness({ profile: data.profile, hasPhoto: Boolean(photo || user?.avatar_url), statuses: journey.statuses })} />
          <Tabs tabs={TABS} value={tab} onChange={goTo} idPrefix={idPrefix} />
          <AnimatePresence mode="wait" initial={false}>
            <m.div key={tab} role="tabpanel" id={`${idPrefix}-panel-${tab}`} aria-labelledby={`${idPrefix}-tab-${tab}`} className="pf-panel"
              variants={swapVariants} initial="initial" animate="enter" exit="exit">
              {tab === 'overview' && (modules.loading && !modules.c01 ? <OverviewSkeleton />
                : <OverviewTab data={data} modules={modules} statuses={journey.statuses} onEdit={() => goTo('edit')} />)}
              {tab === 'edit' && <EditDetailsTab profile={data.profile} onSave={onSave} onCancel={() => push('Changes discarded.', 'info')} onDirtyChange={setDirty} />}
              {tab === 'account' && <AccountTab account={data.account} toast={push} />}
              {tab === 'privacy' && <PrivacyTab data={data} modules={modules} onConsent={onConsent} toast={push} theme={theme} />}
            </m.div>
          </AnimatePresence>
        </>}
    <Toasts items={items} dismiss={dismiss} theme={theme} />
  </div></MotionRoot>
}

function ProfileSkeleton() {
  return <div aria-busy="true" aria-label="Loading your profile">
    <div className="card pf-header pf-skeleton"><div className="pf-identity"><Bone w={96} h={96} r={48} />
      <div className="pf-identity-text"><Bone w={90} h={10} /><Bone w={240} h={26} /><Bone w={200} h={12} /><Bone w={260} h={12} /></div></div>
      <Bone w={92} h={92} r={46} /></div>
    <div className="pf-tabs pf-skeleton">{TABS.map(item => <Bone key={item.value} w={90} h={34} r={10} />)}</div>
    <OverviewSkeleton />
  </div>
}

function OverviewSkeleton() {
  return <div className="pf-overview pf-skeleton" aria-hidden="true">{[0, 1].map(column => <div key={column} className="pf-col">
    {[0, 1].map(card => <div key={card} className="card pf-card"><Bone w="40%" h={16} /><Bone h={12} /><Bone w="85%" h={12} /><Bone w="70%" h={12} /></div>)}
  </div>)}</div>
}
