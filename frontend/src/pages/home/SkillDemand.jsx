// Skill demand: share of listings that name each tracked skill. Skills found in the student's
// own CV (Component 01) are marked, so the market data reads as personal.
import { useState } from 'react'
import { hasSkill } from './homeUtils.js'
import { formatCount } from './marketApi.js'
import { CardHeader, Segmented, useSeen } from './ui.jsx'

const TOP = 12

export default function SkillDemand({ skills, cvSkills }) {
  const [view, setView] = useState('top')
  const [ref, seen] = useSeen(0.2)
  const all = skills.skills
  const rows = view === 'top' ? all.slice(0, TOP) : all
  const peak = all[0]?.listings || 1
  const owned = cvSkills.length ? rows.filter(skill => hasSkill(skill.skill, cvSkills)).length : 0
  return <section id="skill-demand" className="card mp-card" aria-labelledby="skills-title">
    <CardHeader id="skills-title" title="Skill demand" hint={skills.listings_with_skills ? `Share of the ${formatCount(skills.listings_with_skills)} listings that name a tracked skill` : 'Most requested technical skills'}>
      {all.length > TOP && <Segmented label="Skills shown" value={view} onChange={setView} options={[{ value: 'top', label: `Top ${TOP}` }, { value: 'all', label: `All ${all.length}` }]} />}
    </CardHeader>
    {!all.length ? <p className="mp-empty">No tracked skill was mentioned in this market's listings.</p> : <>
      <p className="skill-legend">{cvSkills.length
        ? <><span className="skill-owned-key" aria-hidden="true">✓</span>{owned} of these {rows.length} skills appear in your CV.</>
        : 'Upload your CV to see which of these skills you already have.'}</p>
      <ol className={`skill-bars ${seen ? 'is-in' : ''}`} ref={ref}>
        {rows.map((skill, index) => {
          const mine = cvSkills.length > 0 && hasSkill(skill.skill, cvSkills)
          return <li key={skill.skill} className={mine ? 'is-mine' : ''} style={{ '--i': Math.min(index, 14) }}
            title={`${skill.skill}: ${formatCount(skill.listings)} listings${skill.share_pct == null ? '' : `, ${skill.share_pct.toFixed(1)}%`}`}>
            <span className="skill-name">{skill.skill}{mine && <span className="skill-owned"><span aria-hidden="true">✓</span><span className="sr-only">, in your CV</span></span>}</span>
            <span className="skill-track" aria-hidden="true"><i style={{ '--w': skill.listings / peak }} /></span>
            <span className="skill-value">{formatCount(skill.listings)}<small>{skill.share_pct == null ? '' : `${skill.share_pct.toFixed(1)}%`}</small></span>
          </li>
        })}
      </ol>
    </>}
  </section>
}
