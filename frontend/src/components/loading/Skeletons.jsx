// Skeleton placeholders shaped like the content they stand in for. Decorative only:
// the loading announcement comes from AILoader or the optional `label`.
import './loading.css'

export function Bone({ w = '100%', h = 12, r, className = '' }) {
  return <span className={`sk-bone ${className}`} style={{ width: w, height: h, borderRadius: r }} />
}

function SkeletonCard({ className = '', children }) {
  return <div className={`card sk-card ${className}`}>{children}</div>
}

function Lines({ count = 3 }) {
  return <div className="sk-lines">{Array.from({ length: count }, (_, i) => <Bone key={i} w={i === count - 1 ? '62%' : '100%'} h={10} />)}</div>
}

function Status({ label }) {
  return label ? <span className="sr-only" role="status">{label}</span> : null
}

// Summary card and a grid of result cards (Component 01 results, Component 02 profile).
export function SkeletonDashboard({ cards = 4, label }) {
  return <div className="sk-stack">
    <Status label={label} />
    <div aria-hidden="true" className="sk-stack">
      <SkeletonCard><Bone w={150} h={24} r={6} /><Bone w="45%" h={18} className="sk-gap" /><Lines count={2} /></SkeletonCard>
      <div className="sk-grid">{Array.from({ length: cards }, (_, i) => <SkeletonCard key={i}>
        <div className="sk-row"><Bone w="40%" h={16} /><Bone w={56} h={22} /></div>
        <div className="sk-segments">{[1, 2, 3, 4, 5].map(n => <Bone key={n} h={5} />)}</div>
        <Lines count={3} />
      </SkeletonCard>)}</div>
    </div>
  </div>
}

// Best-match hero with score ring, reason/factor cards and the top-five list (Component 03).
export function SkeletonCareer({ label }) {
  return <div className="sk-stack">
    <Status label={label} />
    <div aria-hidden="true" className="sk-stack">
      <div className="sk-hero sk-card">
        <div className="sk-lines"><Bone w={170} h={10} /><Bone w="55%" h={30} /><Bone w="80%" h={10} /><Bone w="65%" h={10} /><div className="sk-row sk-start"><Bone w={150} h={24} r={999} /><Bone w={120} h={24} r={999} /></div></div>
        <Bone w={130} h={130} r="50%" className="sk-ring" />
      </div>
      <div className="sk-grid">
        <SkeletonCard><Bone w="45%" h={16} /><Bone w="65%" h={10} className="sk-gap" />{[0, 1, 2, 3].map(i => <div key={i} className="sk-row sk-start"><Bone w={26} h={26} r={8} /><Bone w={`${85 - i * 9}%`} h={10} /></div>)}</SkeletonCard>
        <SkeletonCard><Bone w="50%" h={16} /><Bone w="70%" h={10} className="sk-gap" />{[78, 62, 48, 35, 22].map(w => <div key={w} className="sk-factor"><Bone h={10} /><Bone w={`${w}%`} h={10} /><Bone h={10} /></div>)}</SkeletonCard>
      </div>
      <SkeletonCard><Bone w="35%" h={16} /><Bone w="50%" h={10} className="sk-gap" />{[92, 84, 76, 70, 63].map(w => <div key={w} className="sk-job"><Bone w={32} h={32} r={10} /><Bone w="70%" h={12} /><Bone w={`${w}%`} h={8} /><Bone h={14} /></div>)}</SkeletonCard>
    </div>
  </div>
}

// Readiness score ring with factor bars, then skill-gap rows (Component 04 results).
export function SkeletonSkillGap({ rows = 5, label }) {
  return <div className="sk-stack">
    <Status label={label} />
    <div aria-hidden="true" className="sk-stack">
      <SkeletonCard>
        <div className="sk-row sk-start"><Bone w={30} h={30} r={8} /><Bone w="35%" h={18} /></div>
        <div className="sk-readiness"><Bone w={128} h={128} r="50%" className="sk-ring" /><div className="sk-lines">{[90, 72, 60, 48, 36].map(w => <div key={w} className="sk-factor"><Bone h={10} /><Bone w={`${w}%`} h={10} /><Bone h={10} /></div>)}</div></div>
      </SkeletonCard>
      <SkeletonCard>
        <div className="sk-row sk-start"><Bone w={30} h={30} r={8} /><Bone w="30%" h={18} /></div>
        {Array.from({ length: rows }, (_, i) => <div key={i} className="sk-gap-row"><Bone w={`${70 - (i % 3) * 12}%`} h={12} /><div className="sk-segments">{[1, 2, 3, 4, 5].map(n => <Bone key={n} h={8} />)}</div><Bone w={72} h={22} r={999} /></div>)}
      </SkeletonCard>
    </div>
  </div>
}

// Staged learning roadmap timeline (Component 04).
export function SkeletonRoadmap({ stages = 3, label }) {
  return <div className="sk-stack">
    <Status label={label} />
    <SkeletonCard className="sk-timeline-card">
      <div aria-hidden="true">
        <div className="sk-row sk-start"><Bone w={30} h={30} r={8} /><Bone w="32%" h={18} /></div>
        <ol className="sk-timeline">{Array.from({ length: stages }, (_, i) => <li key={i}><span className="sk-node" /><div className="sk-lines"><Bone w="38%" h={14} /><Bone w="85%" h={10} /><div className="sk-row sk-start"><Bone w={90} h={22} r={999} /><Bone w={110} h={22} r={999} /><Bone w={70} h={22} r={999} /></div></div></li>)}</ol>
      </div>
    </SkeletonCard>
  </div>
}

// Questionnaire and assessment forms (Components 02 and 04).
export function SkeletonForm({ fields = 4, label }) {
  return <div className="sk-stack">
    <Status label={label} />
    <SkeletonCard>
      <div aria-hidden="true" className="sk-lines">
        <div className="sk-row"><Bone w="40%" h={20} /><Bone w={70} h={34} r={8} /></div>
        <Bone w="85%" h={10} /><Bone h={6} r={6} className="sk-gap" />
        {Array.from({ length: fields }, (_, i) => <div key={i} className="sk-field"><Bone w={`${75 - (i % 3) * 10}%`} h={13} /><div className="sk-options">{[1, 2, 3, 4, 5].map(n => <Bone key={n} h={38} r={8} />)}</div></div>)}
        <div className="sk-row"><Bone w={90} h={42} r={8} /><Bone w={150} h={42} r={8} /></div>
      </div>
    </SkeletonCard>
  </div>
}
