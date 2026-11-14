// Overview: the career journey (real module status), a summary of each module's result, the CV
// record and the saved details. Read-only; every summary links to its module.
import { Link, useNavigate } from 'react-router-dom'
import Icon from '../../components/Icon.jsx'
import { Reveal, RevealItem } from '../home/MotionRoot.jsx'
import { STEPS } from '../home/journeyStatus.js'
import { REGIONS, WORK_TYPES, cvName } from './profileModel.js'
import { EmptyModule, formatDate } from './profileUi.jsx'

const STATUS = { done: 'Done', 'in-progress': 'In progress', ready: 'Not started', locked: 'Needs your CV' }

export default function OverviewTab({ data, modules, statuses, onEdit }) {
  const c01 = modules.c01?.value
  const updated = {
    c01: formatDate(c01?.assessedAt),
    c02: modules.c02?.value ? 'Saved in this browser session' : null,
    c03: c01 ? `From your CV assessed ${formatDate(c01.assessedAt)}` : null,
    c04: formatDate(modules.c04?.value?.record?.submitted_at),
  }
  return <div className="pf-overview">
    <div className="pf-col">
      <Reveal as="section" className="card pf-card" aria-labelledby="pf-journey-title">
        <header className="card-head"><div><h3 id="pf-journey-title">My career journey</h3><p>Status from each module, for this account in this browser.</p></div></header>
        <ol className="pf-steps">
          {STEPS.map(step => {
            const status = statuses[step.key] || 'ready'
            return <RevealItem as="li" key={step.key} className={`pf-step is-${status}`}>
              <span className="pf-step-node" aria-hidden="true">{status === 'done' ? <Icon name="check" size={15} /> : step.number}</span>
              <Link to={step.to} className="pf-step-body">
                <strong>{step.label}</strong>
                <small>{updated[step.key] ? `Last updated: ${updated[step.key]}` : 'No result yet'}</small>
              </Link>
              <span className={`pf-status is-${status}`}>{STATUS[status]}</span>
            </RevealItem>
          })}
        </ol>
      </Reveal>
      <Skills module={modules.c01} />
      <Personality module={modules.c02} />
    </div>
    <div className="pf-col">
      <Careers module={modules.c03} hasCv={Boolean(c01)} />
      <Roadmap module={modules.c04} />
      <CvCard cv={data.cv} assessedAt={c01?.assessedAt} />
      <About profile={data.profile} onEdit={onEdit} />
    </div>
  </div>
}

function ModuleCard({ id, title, to, linkLabel, error, children }) {
  return <Reveal as="section" className="card pf-card" aria-labelledby={id}>
    <header className="card-head"><div><h3 id={id}>{title}</h3></div>
      {to && <Link className="pf-card-link" to={to}>{linkLabel} <span aria-hidden="true">→</span></Link>}</header>
    {error ? <p className="pf-error" role="alert">{error}</p> : children}
  </Reveal>
}

function Skills({ module }) {
  const value = module?.value
  return <ModuleCard id="pf-skills" title="Skills" to={value ? '/component01' : null} linkLabel="View full assessment" error={module?.error}>
    {value ? <>
      <ul className="pf-skill-chips">{value.top.map(skill => <li key={skill.name}><span>{skill.name}</span><small aria-label={`level ${skill.level} of 5`}>L{skill.level}</small></li>)}</ul>
      <p className="pf-muted">Top {value.top.length} of {value.details.skills.length} skills read from your CV. Levels are estimates from CV evidence, from 1 to 5.</p>
    </> : <EmptyModule icon="skill" text="Upload your CV to see the skills we can read from it." to="/component01" action="Start skill assessment" />}
  </ModuleCard>
}

function Personality({ module }) {
  const value = module?.value
  const traits = value?.traits
  return <ModuleCard id="pf-personality" title="Personality" to={value ? '/component02' : null} linkLabel="View analysis">
    {traits ? <>
      <ul className="pf-traits">{traits.map(trait => <li key={trait.code}>
        <div><strong>{trait.name}</strong><small>{trait.note}</small></div>
        <span className="pf-meter" role="img" aria-label={`${trait.name}: ${Math.round(trait.level * 100)} out of 100`}><i style={{ '--v': trait.level }} /></span>
      </li>)}</ul>
      <p className="pf-muted">From your Big Five questionnaire. Component 02 keeps this in your browser session only.</p>
    </> : value ? <EmptyModule icon="personality" text="You have started the personality analysis. Finish the questionnaire to see your traits here." to="/component02" action="Continue analysis" />
      : <EmptyModule icon="personality" text="Take the personality analysis to see your work-style traits." to="/component02" action="Start personality analysis" />}
  </ModuleCard>
}

function Careers({ module, hasCv }) {
  const value = module?.value
  return <ModuleCard id="pf-careers" title="Career prediction" to={value ? '/component03' : null} linkLabel="View" error={module?.error}>
    {value ? <>
      <ol className="pf-careers">{value.top.map(job => <li key={job.job}>
        <span className="pf-rank">{job.ranking}</span><strong>{job.job}</strong>
        <span className="pf-score"><b>{Math.round(job.score)}%</b><small>match</small></span>
      </li>)}</ol>
      <p className="pf-muted">Match scores come from skill evidence in your CV. They are not hiring probabilities.</p>
    </> : <EmptyModule icon="career" text={hasCv ? 'Career matches are not available yet. Open Career prediction to load them.' : 'Your career matches appear after your CV is assessed.'}
      to={hasCv ? '/component03' : '/component01'} action={hasCv ? 'Open career prediction' : 'Upload your CV first'} />}
  </ModuleCard>
}

function Roadmap({ module }) {
  const value = module?.value
  const progress = value?.progress
  return <ModuleCard id="pf-roadmap" title="Learning roadmap" to={value ? '/component04' : null} linkLabel="Continue roadmap" error={module?.error}>
    {value ? <>
      <p className="pf-roadmap-career">For <strong>{value.record.career_name}</strong>
        {value.record.readiness_score != null && <> · readiness <strong>{Math.round(value.record.readiness_score)}/100</strong> when submitted</>}</p>
      {progress ? <>
        <div className="pf-progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress.percent}
          aria-label={`${progress.met} of ${progress.total} required skills met`}><i style={{ '--v': progress.percent / 100 }} /></div>
        <p className="pf-progress-label"><strong>{progress.percent}%</strong> of required skills met ({progress.met} of {progress.total})</p>
        {progress.next ? <p className="pf-next"><span>Next step</span><strong>{progress.next.skill_name}</strong>{progress.next.reason && <small>{progress.next.reason}</small>}</p>
          : <p className="pf-next"><span>Next step</span><strong>Every requirement is met. Keep your CV evidence current.</strong></p>}
      </> : <p className="pf-muted">{value.analysisError ? `Progress could not be calculated right now: ${value.analysisError}` : 'Open the roadmap to see your progress.'}</p>}
    </> : <EmptyModule icon="roadmap" text="Choose a target career to get your readiness score and a step-by-step plan." to="/component04" action="Build my roadmap" />}
  </ModuleCard>
}

function CvCard({ cv, assessedAt }) {
  const navigate = useNavigate()
  const name = cvName(cv, assessedAt)
  return <Reveal as="section" className="card pf-card" aria-labelledby="pf-cv">
    <header className="card-head"><div><h3 id="pf-cv">CV</h3></div></header>
    {assessedAt ? <div className="pf-cv-row">
      <span className="pf-cv-icon"><Icon name="document" size={20} /></span>
      <div><strong>{name || 'File name not recorded'}</strong><small>Assessed {formatDate(assessedAt)}</small></div>
    </div> : <p className="pf-muted">No CV has been assessed yet.</p>}
    <p className="pf-note">We don’t keep your CV file. Only the skills read from it{name ? ' and the file name' : ''} are saved.</p>
    <button type="button" className="button pf-button-sm" onClick={() => navigate('/', { state: { scrollTo: 'cv-upload' } })}>
      <Icon name="upload" size={15} />{assessedAt ? 'Upload new CV' : 'Upload your CV'}</button>
  </Reveal>
}

function About({ profile, onEdit }) {
  const label = (list, value) => list.find(item => item.value === value)?.label
  const rows = [
    ['Location', profile.location], ['University', profile.university], ['Degree programme', profile.degree],
    ['Academic year', profile.academic_year], ['Graduation year', profile.graduation_year],
    ['Preferred work type', label(WORK_TYPES, profile.work_type)], ['Preferred region', label(REGIONS, profile.region)],
  ]
  const filled = rows.filter(([, value]) => value)
  const empty = !filled.length && !profile.bio && !profile.interests.length && !profile.linkedin_url && !profile.github_url
  return <Reveal as="section" className="card pf-card" aria-labelledby="pf-about">
    <header className="card-head"><div><h3 id="pf-about">About me</h3></div>
      <button type="button" className="pf-card-link" onClick={onEdit}>Edit details <span aria-hidden="true">→</span></button></header>
    {empty ? <p className="pf-muted">You haven’t added any details yet. They help you keep your study and career goals in one place.</p> : <>
      {profile.bio && <p className="pf-bio">{profile.bio}</p>}
      {filled.length > 0 && <dl className="pf-facts">{filled.map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl>}
      {profile.interests.length > 0 && <ul className="pf-interest-list" aria-label="Career interests">{profile.interests.map(item => <li key={item}>{item}</li>)}</ul>}
      {(profile.linkedin_url || profile.github_url) && <p className="pf-links">
        {profile.linkedin_url && <a href={profile.linkedin_url} target="_blank" rel="noreferrer">LinkedIn <span className="sr-only">(opens in a new tab)</span></a>}
        {profile.github_url && <a href={profile.github_url} target="_blank" rel="noreferrer">GitHub <span className="sr-only">(opens in a new tab)</span></a>}
      </p>}
    </>}
  </Reveal>
}
