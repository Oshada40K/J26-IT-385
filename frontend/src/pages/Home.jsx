import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { uploadCV } from './component01/skillApi.js'
import Icon from '../components/Icon.jsx'

export default function Home() {
  const navigate = useNavigate()
  const [uploading, setUploading] = useState(false)
  const input = useRef(null)
  const dragDepth = useRef(0)
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)

  function selectFile(files) {
    if (uploading || !files?.length) return
    const selected = files[0]
    if (files.length > 1) { setError('Please choose one CV at a time.'); return }
    if (!/\.(pdf|docx)$/i.test(selected.name)) { setError('Please choose a PDF or DOCX file.'); return }
    if (!selected.size || selected.size > 10 * 1024 * 1024) { setError('Choose a file between 1 byte and 10 MB.'); return }
    setFile(selected)
    setError('')
  }

  async function analyzeCV() {
    if (!file || uploading) return
    setUploading(true)
    setError('')
    try {
      await uploadCV(file)
      navigate('/component01')
    } catch (err) { setError(err.message) }
    finally { setUploading(false) }
  }

  return <div className="page home-page">
    <section className="home-intro">
      <h1>Big possibilities.<br /><span>Start with your CV.</span></h1>
    </section>
    <section className="cv-panel" aria-labelledby="cv-title">
      <div className="cv-art" aria-hidden="true">
        <div className="cv-art-ring" />
        <span className="cv-spark spark-one"><Icon size={20} /></span>
        <span className="cv-spark spark-two"><Icon size={12} /></span>
        <div className="cv-paper"><div className="cv-paper-heading"><span /><div><i /><i /></div></div><div className="cv-paper-rule" /><i className="cv-paper-line long" /><i className="cv-paper-line" /><i className="cv-paper-line short" /><div className="cv-paper-tags"><span /><span /><span /></div><i className="cv-paper-line long" /><i className="cv-paper-line" /></div>
        <span className="cv-art-badge"><Icon name="check" size={16} /></span>
      </div>
      <h2 id="cv-title">Your journey, in one document.</h2>
      <div className={`cv-dropzone ${dragging ? 'is-dragging' : ''} ${file ? 'has-file' : ''}`}
        onDragEnter={event => { event.preventDefault(); dragDepth.current += 1; setDragging(true) }}
        onDragOver={event => { event.preventDefault(); event.dataTransfer.dropEffect = 'copy' }}
        onDragLeave={event => { event.preventDefault(); dragDepth.current -= 1; if (dragDepth.current <= 0) setDragging(false) }}
        onDrop={event => { event.preventDefault(); dragDepth.current = 0; setDragging(false); selectFile(event.dataTransfer.files) }}>
        <input ref={input} className="cv-file-input" type="file" disabled={uploading} accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" aria-label="Choose your CV" aria-describedby="cv-formats cv-feedback" onChange={event => { selectFile(event.target.files); event.target.value = '' }} />
        {file ? <div className="cv-selected"><span className="cv-file-icon"><Icon name="document" size={24} /></span><div><strong>{file.name}</strong><span>{(file.size / 1024 / 1024).toFixed(2)} MB · Selected</span></div><button className="cv-remove" disabled={uploading} aria-label="Remove selected CV" onClick={() => { setFile(null); setError('') }}><Icon name="close" size={18} /></button></div> : <><span className="cv-upload-icon"><Icon name="upload" size={24} /></span><strong>{dragging ? 'Drop your CV here' : 'Drag & drop your CV here'}</strong></>}
        <button className="cv-browse" disabled={uploading} onClick={() => input.current?.click()}><Icon name={file ? 'document' : 'upload'} size={17} />{file ? 'Choose another CV' : 'Choose your CV'}<Icon name="arrow" size={17} /></button>
        {file && <button className="cv-analyze" disabled={uploading} onClick={analyzeCV}>{uploading ? 'Assessing your CV…' : 'Analyze my CV'}<Icon name="arrow" size={17} /></button>}
        <small id="cv-formats">PDF or DOCX · Up to 10 MB</small>
      </div>
      <div id="cv-feedback" aria-live="polite" aria-atomic="true">{error && <p className="cv-error" role="alert">{error}</p>}{uploading && <p className="cv-selection-note" role="status">Extracting skills and reviewing CV evidence…</p>}</div>
      <p className="cv-local-note">Your CV is processed for skill evidence. The original file is not retained.</p>
    </section>
    <div className="home-next"><div><Link to="/component01"><Icon name="skill" size={17} />Your strengths</Link><i /><Link to="/component03"><Icon name="career" size={17} />Career possibilities</Link><i /><Link to="/component04"><Icon name="roadmap" size={17} />Your next steps</Link></div></div>
  </div>
}
