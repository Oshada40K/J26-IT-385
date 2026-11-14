// CV upload card. Same upload, validation and redirect as before: Component 01 assesses the CV,
// Component 03 predicts careers, then the student is taken to /component03 with the result.
// The staged status follows the two real requests; nothing advances on a timer.
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, m } from 'motion/react'
import { savedSession, uploadCV } from '../component01/skillApi.js'
import { uploadAndPredictCV } from '../component03/careerApi.js'
import { API_BASE_URL } from '../../api/client.js'
import { invalidate } from '../../api/resourceCache.js'
import Icon from '../../components/Icon.jsx'
import { fileProblem } from './homeUtils.js'
import { markCvAssessed } from './journey.js'
import { recordCvUpload } from '../profile/profileApi.js'
import { swapVariants } from './motion.js'
import { useReducedMotion } from './MotionRoot.jsx'

const STAGES = [
  { key: 'read', label: 'Reading your CV' },
  { key: 'extract', label: 'Extracting skills' },
  { key: 'map', label: 'Mapping careers' },
]
const CONFETTI = Array.from({ length: 14 }, (_, i) => {
  const angle = (i / 14) * Math.PI * 2
  const distance = 54 + (i % 3) * 16
  return { dx: Math.cos(angle) * distance, dy: Math.sin(angle) * distance, tone: i % 3 }
})

export default function HeroUpload() {
  const navigate = useNavigate()
  const reduced = useReducedMotion()
  const [phase, setPhase] = useState('idle') // idle | uploading | predicting | success
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)
  const processing = useRef(false)
  const input = useRef(null)
  const card = useRef(null)
  const dragDepth = useRef(0)
  const leave = useRef(null)
  const busy = phase === 'uploading' || phase === 'predicting'

  useEffect(() => () => clearTimeout(leave.current), [])

  // A gentle shake on errors (transform only, skipped for reduced motion; focus stays put).
  function fail(message) {
    setError(message)
    if (!reduced && card.current?.animate) {
      card.current.animate([{ transform: 'none' }, { transform: 'translateX(-6px)' }, { transform: 'translateX(5px)' }, { transform: 'translateX(-3px)' }, { transform: 'none' }], { duration: 380, easing: 'ease-out' })
    }
  }

  function selectFile(files) {
    if (busy || !files?.length) return
    const problem = fileProblem(files)
    if (problem) { fail(problem); return }
    setFile(files[0])
    setError('')
  }

  async function analyzeCV() {
    if (!file || processing.current) return
    processing.current = true
    setPhase('uploading')
    setError('')
    try {
      const prediction = await uploadAndPredictCV(file, {
        uploadCV, savedSession, baseUrl: API_BASE_URL,
        onAssessed: () => {
          setPhase('predicting')
          recordCvUpload(file.name).catch(() => {}) // the profile shows the last CV's name; never blocks the upload
        },
      })
      invalidate() // a new CV changes skills, career matches and roadmap data
      markCvAssessed(prediction.candidateId)
      setPhase('success')
      leave.current = setTimeout(() => navigate('/component03', { state: prediction }), reduced ? 350 : 1300)
      processing.current = { prediction }
    } catch (err) {
      invalidate()
      processing.current = false
      setPhase('idle')
      fail(err.message)
    }
  }

  function openResults() {
    clearTimeout(leave.current)
    navigate('/component03', { state: processing.current?.prediction })
  }

  function magnet(event) {
    if (reduced) return
    const box = event.currentTarget.getBoundingClientRect()
    const dx = Math.max(-6, Math.min(6, (event.clientX - box.left - box.width / 2) * 0.12))
    const dy = Math.max(-4, Math.min(4, (event.clientY - box.top - box.height / 2) * 0.2))
    event.currentTarget.style.setProperty('--mx', `${dx}px`)
    event.currentTarget.style.setProperty('--my', `${dy}px`)
  }
  const unmagnet = event => { event.currentTarget.style.setProperty('--mx', '0px'); event.currentTarget.style.setProperty('--my', '0px') }

  const stageState = key => phase === 'success' ? 'done'
    : phase === 'predicting' ? (key === 'map' ? 'active' : 'done')
      : phase === 'uploading' ? (key === 'map' ? 'pending' : 'active') : 'pending'

  return <section id="cv-upload" className="upload-card" aria-labelledby="cv-title" aria-busy={busy}>
    <div ref={card} className="upload-inner">
      <div className="upload-head">
        <span className="upload-head-icon" aria-hidden="true"><Icon name="document" size={20} /></span>
        <div><h2 id="cv-title">Your journey, in one document.</h2><p>We read the skill evidence in your CV, then match it to careers.</p></div>
      </div>
      <AnimatePresence mode="wait" initial={false}>
        {phase === 'idle' && <m.div key="drop" variants={swapVariants} initial="initial" animate="enter" exit="exit">
          <div className={`dropzone ${dragging ? 'is-dragging' : ''} ${file ? 'has-file' : ''}`}
            onDragEnter={event => { event.preventDefault(); dragDepth.current += 1; setDragging(true) }}
            onDragOver={event => { event.preventDefault(); event.dataTransfer.dropEffect = 'copy' }}
            onDragLeave={event => { event.preventDefault(); dragDepth.current -= 1; if (dragDepth.current <= 0) setDragging(false) }}
            onDrop={event => { event.preventDefault(); dragDepth.current = 0; setDragging(false); selectFile(event.dataTransfer.files) }}>
            <svg className="dropzone-ants" aria-hidden="true"><rect x="1" y="1" rx="15" ry="15" /></svg>
            <input ref={input} className="cv-file-input" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              aria-label="Choose your CV" aria-describedby="cv-formats cv-feedback" onChange={event => { selectFile(event.target.files); event.target.value = '' }} />
            {file ? <div className="file-row">
              <span className="file-icon" aria-hidden="true"><Icon name="document" size={22} /></span>
              <div><strong>{file.name}</strong><span>{(file.size / 1024 / 1024).toFixed(2)} MB · Selected</span></div>
              <button type="button" className="file-remove" aria-label="Remove selected CV" onClick={() => { setFile(null); setError('') }}><Icon name="close" size={18} /></button>
            </div> : <>
              <span className="drop-icon" aria-hidden="true"><Icon name="upload" size={24} /></span>
              <strong className="drop-title">{dragging ? 'Drop your CV here' : 'Drag & drop your CV here'}</strong>
              <span className="drop-or">or</span>
            </>}
            <div className="drop-actions">
              <button id="cv-choose" type="button" className={file ? 'choose choose-quiet' : 'choose magnetic'} onPointerMove={file ? undefined : magnet} onPointerLeave={file ? undefined : unmagnet} onClick={() => input.current?.click()}>
                <Icon name={file ? 'document' : 'upload'} size={17} />{file ? 'Choose another CV' : 'Choose your CV'}<span className="nudge" aria-hidden="true"><Icon name="arrow" size={17} /></span>
              </button>
              {file && <button type="button" className="analyze magnetic" onPointerMove={magnet} onPointerLeave={unmagnet} onClick={analyzeCV}>Analyze my CV<span className="nudge" aria-hidden="true"><Icon name="arrow" size={17} /></span></button>}
            </div>
            <small id="cv-formats">PDF or DOCX · Up to 10 MB</small>
          </div>
        </m.div>}
        {busy && <m.div key="scan" className="scan" variants={swapVariants} initial="initial" animate="enter" exit="exit">
          <div className="scan-doc" aria-hidden="true">
            <div className="scan-paper"><i className="w70" /><i className="w45" /><span className="scan-rule" /><i /><i className="w80" /><i className="w55" /><span className="scan-tags"><b /><b /><b /></span><i /><i className="w70" /></div>
            <span className="scan-beam" />
          </div>
          <div className="scan-copy">
            <strong>{file?.size ? `${(file.size / 1024 / 1024).toFixed(2)} MB CV` : 'Your CV'}</strong>
            <ol className="stages">{STAGES.map(stage => <li key={stage.key} className={`is-${stageState(stage.key)}`}>
              <span className="stage-mark" aria-hidden="true">{stageState(stage.key) === 'done' ? <Icon name="check" size={13} /> : null}</span>{stage.label}
              <span className="sr-only">: {stageState(stage.key) === 'done' ? 'done' : stageState(stage.key) === 'active' ? 'in progress' : 'waiting'}</span>
            </li>)}</ol>
          </div>
        </m.div>}
        {phase === 'success' && <m.div key="done" className="done" variants={swapVariants} initial="initial" animate="enter" exit="exit">
          <span className="done-mark" aria-hidden="true">
            {!reduced && CONFETTI.map((piece, i) => <i key={i} className={`confetti tone-${piece.tone}`} style={{ '--dx': `${piece.dx}px`, '--dy': `${piece.dy}px` }} />)}
            <svg width="64" height="64" viewBox="0 0 64 64"><circle cx="32" cy="32" r="29" /><path d="m20 33 8 8 17-18" /></svg>
          </span>
          <strong>Your CV is analysed</strong>
          <p>Your skills are assessed and your career matches are ready.</p>
          <button type="button" className="analyze" onClick={openResults}>See your career matches<span className="nudge" aria-hidden="true"><Icon name="arrow" size={17} /></span></button>
        </m.div>}
      </AnimatePresence>
      <div id="cv-feedback" aria-live="polite" aria-atomic="true">
        {error && <p className="cv-error" role="alert">{error}</p>}
        {busy && <p className="cv-status" role="status">{phase === 'predicting' ? 'Your CV assessment is complete. Finding your best career, top five jobs, and explanation…' : 'Extracting skills and reviewing CV evidence…'}</p>}
        {phase === 'success' && <p className="cv-status" role="status">Done. Opening your career matches…</p>}
      </div>
      <p className="cv-local-note">Your CV is processed for skill evidence. The original file is not retained.</p>
    </div>
  </section>
}
