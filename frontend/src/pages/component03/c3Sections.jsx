// Owner: Oshada - Component 03 result sections. Presentation only: every number shown comes
// from the career APIs (best-job, top-jobs, explanation, insights) unchanged.
import { useRef, useState } from 'react'
import { useInViewport } from '../home/viewport.js'
import { useCountUp } from '../home/useCountUp.js'
import { Link } from 'react-router-dom'
import Icon from '../../components/Icon.jsx'
import { Accordion, Count, Mark, Section, Tip, useSeen } from './c3Ui.jsx'
import { confidenceShares, gapToTop, isNarrow, isTechnicalFactor, pct, rangeLabel, reasonMatches, zoomAxis } from './c3Model.js'

const RADIUS = 64
const CIRCUMFERENCE = 2 * Math.PI * RADIUS
const arcOffset = score => CIRCUMFERENCE * (1 - Math.max(0, Math.min(100, score)) / 100)

// ---------- 1. Best match hero ----------
// Animation tells the result: your real matched skills flow into the gauge, the rank counts down
// from the number of occupations to #1, and the dial's ticks light up to your score. Ambient
// motion pauses when the hero is off screen; reduced motion turns it off (global CSS rule).
const TICKS = 60
// Start points for the skill pills: spread vertically so they never bunch up.
const STREAM_Y = [-72, 46, -24, 78, -58, 18, -84, 60]

function Gauge({ score, preview, meaning, skills, live }) {
  const [ref, seen] = useSeen(0.4)
  const gain = preview ? preview.new_score - score : 0
  const lit = Math.round((Math.max(0, Math.min(100, score)) / 100) * TICKS)
  return <div ref={ref} className={`c3-gauge ${seen ? 'is-in' : ''}`}>
    <div className="c3-gauge-dial" role="img" aria-label={`Match score ${score.toFixed(1)} out of 100${preview ? `; preview after ${preview.technology}: ${preview.new_score.toFixed(1)}` : ''}`}>
      {/* Matched skills drift into the dial: the score is built from them. */}
      {live && <div className="c3-stream" aria-hidden="true">{skills.slice(0, 8).map((skill, index) => <span key={skill} className="c3-stream-pill"
        style={{ '--x': `${-150 - (index % 3) * 30}px`, '--y': `${STREAM_Y[index]}px`, animationDelay: `${index * 1.4}s` }}>{skill}</span>)}</div>}
      <span className="c3-gauge-pulse" aria-hidden="true" />
      <span className="c3-gauge-orbit" aria-hidden="true" />
      <svg className="c3-gauge-ticks" viewBox="0 0 200 200" aria-hidden="true">
        {Array.from({ length: TICKS }, (_, i) => <line key={i} x1="100" y1="6" x2="100" y2={i % 5 ? 12 : 15} transform={`rotate(${(i / TICKS) * 360} 100 100)`}
          className={i < lit ? 'is-lit' : ''} style={{ '--d': `${300 + i * 18}ms` }} />)}
      </svg>
      <svg className="c3-gauge-ring" viewBox="0 0 150 150" aria-hidden="true">
        <defs><linearGradient id="c3-arc-gradient" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#FDE68A" /><stop offset=".55" stopColor="#FBBF24" /><stop offset="1" stopColor="#F97316" /></linearGradient></defs>
        <circle className="c3-gauge-track" cx="75" cy="75" r={RADIUS} />
        {preview && <circle className="c3-gauge-ghost" cx="75" cy="75" r={RADIUS} strokeDasharray={CIRCUMFERENCE} strokeDashoffset={arcOffset(preview.new_score)} />}
        <circle className="c3-gauge-arc" cx="75" cy="75" r={RADIUS} strokeDasharray={CIRCUMFERENCE} strokeDashoffset={seen ? arcOffset(score) : CIRCUMFERENCE} />
      </svg>
      {/* A bright head sits at the end of the arc once it has drawn. */}
      <span className="c3-gauge-head" style={{ '--a': `${(Math.min(score, 100) / 100) * 360}deg` }} aria-hidden="true"><i /></span>
      <span className="c3-gauge-glow" aria-hidden="true" />
      <div className="c3-gauge-value" aria-hidden="true">
        <strong>{preview ? preview.new_score.toFixed(1) : <Count value={score} active={seen} decimals={1} />}</strong>
        <Tip text={meaning} className="c3-gauge-unit">Match / 100 <Icon name="alert" size={11} /></Tip>
      </div>
      {preview && <span className="c3-gauge-bubble" aria-hidden="true">{gain >= 0 ? '+' : '−'}{Math.abs(gain).toFixed(1)}</span>}
    </div>
    {preview && <p className="c3-gauge-preview" aria-live="polite">Preview: {score.toFixed(1)} → {preview.new_score.toFixed(1)} if you {preview.action === 'learn' ? 'learn' : 'improve'} {preview.technology}</p>}
  </div>
}

// Counts the rank down from the number of occupations to #1.
function RankCountdown({ occupations, active }) {
  const climbed = useCountUp(occupations - 1, { active })
  const rank = active ? Math.max(1, Math.round(occupations - climbed)) : occupations
  return <span className={`c3-rank-badge ${rank === 1 ? 'is-top' : ''}`} aria-hidden="true"><b>#{rank}</b> of {occupations}</span>
}

export function Hero({ heroRef, title, score, occupations, matchedCount, skills = [], uncertainty, meaning, preview, onWhy }) {
  const best = uncertainty?.jobs?.[0]
  const local = useRef(null)
  const visible = useInViewport(local)
  const frame = useRef(0)
  const chips = [
    matchedCount > 0 && { key: 'skills', text: `${matchedCount} of your skills used`, tip: `${matchedCount} technologies from your CV appear in this occupation's O*NET technology list.` },
    { key: 'shap', text: 'Explained with SHAP', tip: 'SHAP splits the score into how much each factor raised or lowered it.' },
    best && { key: 'range', text: `Likely range ${rangeLabel(best.low, best.high)}`, tip: `5th to 95th percentile of the score across ${uncertainty.samples} plausible versions of your CV evidence.` },
    uncertainty && { key: 'stability', text: `Ranking stability: ${uncertainty.stability}`, tip: uncertainty.stability_meaning, tone: uncertainty.stability },
  ].filter(Boolean)
  // A soft spotlight follows the pointer (transform only, one update per frame).
  function onPointerMove(event) {
    if (event.pointerType === 'touch') return
    const box = local.current?.getBoundingClientRect()
    if (!box) return
    const { clientX, clientY } = event
    cancelAnimationFrame(frame.current)
    frame.current = requestAnimationFrame(() => {
      local.current?.style.setProperty('--sx', `${clientX - box.left}px`)
      local.current?.style.setProperty('--sy', `${clientY - box.top}px`)
    })
  }
  const setRefs = node => { local.current = node; if (heroRef) heroRef.current = node }
  return <section ref={setRefs} id="c3-best" className={`c3-hero ${visible ? '' : 'is-paused'}`} aria-labelledby="c3-best-title" onPointerMove={onPointerMove}>
    <div className="c3-hero-sky" aria-hidden="true"><i /><i /><i /><b className="s1">✦</b><b className="s2">✦</b><b className="s3">✦</b><span className="c3-spotlight" /></div>
    <div className="c3-hero-copy">
      <div className="c3-hero-label"><Icon name="spark" size={13} /> YOUR BEST CAREER MATCH <RankCountdown occupations={occupations} active={visible} /></div>
      <h2 id="c3-best-title" className="c3-mask"><span>{title}</span></h2>
      <p>Ranked first out of {occupations} occupations by comparing your CV skills and soft skills with O*NET job requirements.</p>
      <ul className="c3-hero-meta">{chips.map((chip, index) => <li key={chip.key} style={{ '--i': index }}>
        <Tip text={chip.tip} className={`c3-hero-chip ${chip.tone ? `tone-${chip.tone}` : ''}`}>{chip.text}</Tip>
      </li>)}</ul>
      <button type="button" className="c3-why-link" onClick={onWhy}>Why #1? <Icon name="arrow" size={14} /></button>
    </div>
    {score != null && <Gauge score={score} preview={preview} meaning={meaning} skills={skills} live={visible} />}
  </section>
}

// ---------- 2. Why this career + what shaped the score ----------
export function WhySection({ reasons, factors, shapText, focus, onFocus }) {
  const linked = focus ? reasonMatches(focus, reasons) : []
  const max = Math.max(...factors.map(f => Math.abs(f.points)), 1)
  const [ref, seen] = useSeen(0.2)
  return <Section id="c3-why" className="c3-grid">
    <div className="c3-card">
      <h3>Why this career?</h3>
      <p className="c3-card-sub">The main reasons behind your recommendation</p>
      <ul className="c3-reasons">{reasons.map((reason, index) => {
        const down = reason.startsWith('What lowered')
        return <li key={reason} style={{ '--i': index }} className={linked.includes(index) ? 'is-linked' : ''}>
          <span className={`c3-reason-icon ${down ? 'down' : ''}`}><Mark down={down} /></span><span>{reason}</span>
        </li>
      })}</ul>
    </div>
    <div ref={ref} className={`c3-card ${seen ? 'is-in' : ''}`}>
      <h3>What shaped your score</h3>
      <p className="c3-card-sub">Each factor's effect on the match score, in points. Select a factor to see the reason it belongs to.</p>
      <div className="c3-diverge" role="list">
        {factors.map((factor, index) => {
          const up = factor.points >= 0
          const active = focus === factor.label
          return <div role="listitem" key={`${factor.effect}-${factor.label}`} style={{ '--i': index }}>
            <button type="button" className={`c3-factor ${up ? 'up' : 'down'} ${active ? 'is-active' : ''}`} aria-pressed={active}
              onClick={() => onFocus(active ? null : factor.label)}>
              <span className="c3-factor-label">{factor.label}</span>
              <span className="c3-factor-track" aria-hidden="true">
                <i style={{ '--w': Math.max(Math.abs(factor.points) / max, 0.02) }} />
              </span>
              <span className="c3-factor-points">{up ? '+' : '−'}{Math.abs(factor.points).toFixed(1)}</span>
              <span className="c3-factor-tip" aria-hidden="true">This factor {up ? 'added' : 'took away'} {up ? '+' : ''}{factor.points.toFixed(2)} points</span>
              <span className="sr-only">: {up ? 'raised' : 'lowered'} the score by {Math.abs(factor.points).toFixed(2)} points</span>
            </button>
          </div>
        })}
      </div>
      <div className="c3-legend"><span><i />Raised the score</span><span><i className="negative" />Lowered the score</span></div>
      <Accordion title="Technical details (SHAP)"><ul className="c3-shap-text">{shapText.map(line => <li key={line}>{line}</li>)}</ul></Accordion>
    </div>
  </Section>
}

// ---------- 3. Skills ----------
export function SkillsSection({ matched, toLearn, gains, target, highlightMatched, onLearn }) {
  return <Section id="c3-skills" className="c3-grid">
    <div className={`c3-card ${highlightMatched ? 'is-linked' : ''}`}>
      <h3>Your matching skills</h3>
      <p className="c3-card-sub">Skills from your CV that this job uses</p>
      {matched.length ? <ul className="c3-chips">{matched.map((skill, index) => <li key={skill} className="c3-chip have" style={{ '--i': index }}><Mark />{skill}</li>)}</ul>
        : <p className="c3-empty">None found.</p>}
    </div>
    <div className="c3-card">
      <h3>Skills to learn next</h3>
      <p className="c3-card-sub">In-demand tools for this job that your CV doesn't show yet. Select one to see it in What if.</p>
      {toLearn.length ? <ul className="c3-chips">{toLearn.map((skill, index) => {
        const gain = gains[skill]
        return <li key={skill} style={{ '--i': index }}>
          <button type="button" className="c3-chip learn" onClick={() => onLearn(skill)} aria-describedby={`c3-gain-${index}`}>
            <span aria-hidden="true">+</span>{skill}
            <span role="tooltip" id={`c3-gain-${index}`} className="c3-tip-body">{gain
              ? `Learning this to level ${gain.to_level}: +${gain.score_gain.toFixed(2)} for ${target} (single change, model estimate)`
              : 'No what-if score was computed for this skill.'}</span>
          </button>
        </li>
      })}</ul> : <p className="c3-empty">None found.</p>}
      {toLearn.length > 0 && <Link to="/component04" className="c3-cta">
        <span className="c3-cta-icon"><Icon name="roadmap" size={20} /></span>
        <span><strong>Turn these into a step-by-step plan</strong><small>Your Learning roadmap orders them by priority</small></span>
        <Icon name="arrow" size={18} />
      </Link>}
    </div>
  </Section>
}

// ---------- 4. What if ----------
export function WhatIfSection({ cf, preview, pinned, onHover, onPin, flash }) {
  const helpful = cf.actions.filter(a => a.score_gain > 0).slice(0, 5)
  const [ref, seen] = useSeen(0.2)
  return <Section id="c3-whatif" className="c3-card c3-whatif-card">
    <div className="c3-card-head">
      <div><h3>What if you learned…</h3>
        <p className="c3-card-sub">Single skill changes, each re-scored on its own by the model for {cf.target}. Hover or select one to preview it on the score above.</p></div>
      <span className="c3-badge">Single skill change</span>
    </div>
    {helpful.length ? <ul ref={ref} className={`c3-whatif ${seen ? 'is-in' : ''}`}>
      {helpful.map((action, index) => {
        const key = `${action.action}-${action.technology}`
        const active = preview?.technology === action.technology
        return <li key={key} style={{ '--i': index }} data-technology={action.technology}>
          <button type="button" className={`c3-whatif-row ${active ? 'is-active' : ''} ${flash === action.technology ? 'is-flash' : ''}`}
            aria-pressed={pinned?.technology === action.technology}
            onMouseEnter={() => onHover(action)} onMouseLeave={() => onHover(null)} onFocus={() => onHover(action)} onBlur={() => onHover(null)}
            onClick={() => onPin(action)}>
            <span className={`c3-action ${action.action}`}>{action.action === 'learn' ? 'Learn' : 'Improve'}</span>
            <span className="c3-action-text"><strong>{action.technology}</strong>
              <small>{action.action === 'learn' ? `new, to level ${action.to_level}` : `level ${action.from_level} → ${action.to_level}`}</small></span>
            <span className="c3-action-gain">+<Count value={action.score_gain} active={seen} decimals={1} /><small>→ {action.new_score.toFixed(1)}</small></span>
          </button>
        </li>
      })}
    </ul> : <p className="c3-empty">No single skill change raises this score noticeably. Your profile already covers what the model rewards for {cf.target}; the alternatives below show where one new skill matters more.</p>}
    <p className="c3-note">{cf.meaning}</p>
  </Section>
}

// ---------- 5. Other paths ----------
export function PathsSection({ cf }) {
  const path = cf.path_to_runner_up
  const [ref, seen] = useSeen(0.25)
  return <Section id="c3-paths" className="c3-card">
    <h3>Prefer a different path?</h3>
    <p className="c3-card-sub">The one step that moves each alternative closest to the top</p>
    <ul className="c3-alts">{cf.alternatives.map((alt, index) => {
      const share = cf.baseline_score ? Math.min(alt.score / cf.baseline_score, 1) : null
      return <li key={alt.ranking} style={{ '--i': index }}>
        <div className="c3-alt-head"><strong>{alt.job}</strong><span>{alt.gap_to_best.toFixed(2)} pts behind</span></div>
        {share != null && <div className="c3-alt-meter" role="img" aria-label={`Score ${alt.score.toFixed(2)} of the top score ${cf.baseline_score.toFixed(2)}`}><i style={{ '--w': share }} /></div>}
        {alt.best_action ? <p>Learn <span className="c3-pill-skill">{alt.best_action.technology}</span> +{alt.best_action.score_gain.toFixed(1)}{alt.reaches_rank_1 ? ', becomes your best match' : `, rank ${alt.best_action.new_rank}`}</p>
          : <p>No in-demand tool is missing for this job.</p>}
      </li>
    })}</ul>
    {path?.steps?.length > 0 && <div ref={ref} className={`c3-path ${seen ? 'is-in' : ''}`}>
      <strong>{path.reaches_rank_1 ? `Path that makes ${path.job} your best match` : `Three steps towards ${path.job}`}</strong>
      <ol>{path.steps.map((step, index) => <li key={step.technology} style={{ '--i': index }}>
        <span className="c3-path-dot" aria-hidden="true">{index + 1}</span>
        <span>Learn <b>{step.technology}</b></span>
        <span className="c3-path-score">{step.new_score.toFixed(1)} · rank {step.new_rank}{step.becomes_best ? ' ★' : ''}</span>
      </li>)}</ol>
      {!path.reaches_rank_1 && <p className="c3-note">These steps narrow the gap but do not overtake {cf.target}.</p>}
    </div>}
  </Section>
}

// ---------- 6. Confidence ----------
function ProbabilityRing({ value }) {
  const r = 14, c = 2 * Math.PI * r
  return <svg className="c3-prob-ring" width="34" height="34" viewBox="0 0 34 34" aria-hidden="true">
    <circle cx="17" cy="17" r={r} className="track" /><circle cx="17" cy="17" r={r} className="value" strokeDasharray={c} style={{ '--off': c * (1 - value) }} transform="rotate(-90 17 17)" />
  </svg>
}

export function ConfidenceSection({ unc, stability }) {
  const [ref, seen] = useSeen(0.2)
  const shares = confidenceShares(unc.confidence_counts)
  const tiles = [
    { key: 'label', icon: 'pulse', label: 'Explanation stability', value: stability.label, text: true, tip: 'How steady the explanation stays when your CV evidence is varied slightly.' },
    { key: 'top', icon: 'check', label: 'Same top factor', value: pct(stability.top_factor_agreement), suffix: '%', tip: 'How often the biggest factor stays the same across those versions.' },
    { key: 'top3', icon: 'grid', label: 'Top-3 factors kept', value: pct(stability.mean_top3_overlap), suffix: '%', tip: 'How much the three biggest factors overlap across versions, on average.' },
    { key: 'shift', icon: 'arrow', label: 'Avg. factor shift', value: stability.mean_abs_point_change, decimals: 2, suffix: ' pts', tip: 'How many points a factor moves on average between versions. Smaller is steadier.' },
  ]
  return <Section id="c3-confidence" className="c3-card c3-full">
    <h3>How sure is this ranking?</h3>
    <p className="c3-card-sub">{unc.stability_meaning} Bands show the likely score range across {unc.samples} plausible versions of your CV evidence; wider bands come from lower-confidence skills.</p>
    <div ref={ref} className={`c3-ranges ${seen ? 'is-in' : ''}`}>
      {unc.jobs.map((job, index) => {
        const narrow = isNarrow(job.low, job.high)
        return <div className="c3-range" key={job.ranking} style={{ '--i': index }}>
          <span className="c3-range-label" title={job.job}>{job.job}</span>
          <div className="c3-range-track">
            {narrow ? <i className="c3-range-dot" style={{ left: `${job.score}%` }}><em>very stable</em></i>
              : <><span className="c3-range-band" style={{ left: `${job.low}%`, width: `${job.high - job.low}%` }} /><i className="c3-range-point" style={{ left: `${job.score}%` }} /></>}
          </div>
          <span className="c3-range-value">{rangeLabel(job.low, job.high)}</span>
          <span className="c3-range-prob" title="Share of plausible profiles where this job ranked first"><ProbabilityRing value={job.top1_probability} />{pct(job.top1_probability)}% first</span>
        </div>
      })}
    </div>
    <div className="c3-legend">
      <span><i className="band" />Likely score range</span><span><i className="point" />Reported score</span><span><i className="dot" />Range under {0.6} pts: very stable</span>
    </div>
    {shares.length > 0 && <div className="c3-evidence">
      <span>CV evidence confidence</span>
      <div className="c3-evidence-bar" role="img" aria-label={`${unc.confidence_counts.high} high, ${unc.confidence_counts.medium} medium, ${unc.confidence_counts.low} low confidence skills`}>
        {shares.filter(s => s.count).map(s => <i key={s.level} className={s.level} style={{ flexGrow: s.share }} />)}
      </div>
      <small>{unc.confidence_counts.high} high · {unc.confidence_counts.medium} medium · {unc.confidence_counts.low} low</small>
    </div>}
    <div className="c3-stats">{tiles.map(tile => <Tip key={tile.key} as="div" text={tile.tip} className="c3-stat">
      <span className="c3-stat-icon"><Icon name={tile.icon} size={16} /></span>
      <small>{tile.label}</small>
      <strong className={tile.text ? `c3-stability-text ${tile.value}` : undefined}>{tile.text ? tile.value : <Count value={tile.value} active={seen} decimals={tile.decimals || 0} suffix={tile.suffix} />}</strong>
    </Tip>)}</div>
    <p className="c3-note">{stability.meaning}</p>
  </Section>
}

// ---------- 7. Top 5 ----------
export function TopJobsSection({ jobs }) {
  const [zoom, setZoom] = useState(false)
  const [ref, seen] = useSeen(0.2)
  const top = jobs[0].score
  const axis = zoomAxis(jobs.map(j => j.score))
  return <Section id="c3-top5" className="c3-card c3-full">
    <div className="c3-card-head">
      <div><h3>Your top 5 career matches</h3><p className="c3-card-sub">Alternatives worth exploring, ranked by match score</p></div>
      <label className="c3-switch"><input type="checkbox" checked={zoom} onChange={event => setZoom(event.target.checked)} /><span aria-hidden="true" />Zoom to differences</label>
    </div>
    {zoom && <p className="c3-zoom-note" role="status">Axis zoomed to {axis.lo.toFixed(2)}–{axis.hi.toFixed(2)} to show small differences. It does not start at 0.</p>}
    <ol ref={ref} className={`c3-jobs ${seen ? 'is-in' : ''}`}>
      {jobs.map((job, index) => {
        const gap = gapToTop(job.score, top)
        const width = zoom ? axis.position(job.score) : job.score
        return <li key={job.ranking} className={`c3-job ${job.ranking === 1 ? 'best' : ''}`} style={{ '--i': index }}>
          <span className="c3-rank">{job.ranking === 1 ? <span aria-hidden="true">★</span> : job.ranking}<span className="sr-only">Rank {job.ranking}</span></span>
          <span className="c3-job-title">{job.job}
            <span className="c3-job-tag">{job.ranking === 1 ? 'Best match' : gap.tied ? <b className="c3-tie">Tied for #1</b> : `${gap.label} vs #1`}</span></span>
          <div className="c3-bar" aria-hidden="true"><i style={{ '--w': Math.max(width, 1) / 100 }} /></div>
          <span className="c3-job-score">{job.score.toFixed(2)}</span>
        </li>
      })}
    </ol>
  </Section>
}

// ---------- 8. Method ----------
export function MethodSection({ data }) {
  const [ref, seen] = useSeen(0.25)
  const tiles = [
    { icon: 'pulse', label: 'Model', value: 'XGBoost + SHAP' },
    { icon: 'document', label: 'Job data', value: `O*NET ${data.onet_version}` },
    { icon: 'career', label: 'Occupations compared', count: data.eligible_occupations },
    { icon: 'grid', label: 'Features per job', count: 21 },
  ]
  const steps = [
    { label: 'CV skills (C01)', tip: 'Technical skills and levels read from your CV in Skill assessment.' },
    { label: 'Soft skills (C02)', tip: 'Soft-skill levels from your Personality analysis.' },
    { label: `21 features × ${data.eligible_occupations} jobs`, tip: 'Your profile is compared with every occupation on 21 match features.' },
    { label: 'XGBoost score', tip: 'A gradient-boosted tree model turns the features into a 0–100 match score.' },
    { label: 'SHAP explanation', tip: 'SHAP shows how many points each factor added or took away.' },
    { label: 'What-if + confidence', tip: 'Skill changes and varied CV evidence are re-scored to test the ranking.' },
  ]
  return <Section id="c3-method" className="c3-card c3-full">
    <h3>How this recommendation works</h3>
    <p className="c3-card-sub">{data.score_meaning}.</p>
    <div ref={ref} className="c3-stats">{tiles.map(tile => <div key={tile.label} className="c3-stat">
      <span className="c3-stat-icon"><Icon name={tile.icon} size={16} /></span><small>{tile.label}</small>
      <strong>{tile.count != null ? <Count value={tile.count} active={seen} /> : tile.value}</strong>
    </div>)}</div>
    <ol className={`c3-flow ${seen ? 'is-in' : ''}`}>{steps.map((step, index) => <li key={step.label} style={{ '--i': index }}>
      <Tip text={step.tip} className="c3-flow-node">{step.label}</Tip>
      {index < steps.length - 1 && <span className="c3-flow-line" aria-hidden="true"><i /></span>}
    </li>)}</ol>
  </Section>
}

export { isTechnicalFactor }
