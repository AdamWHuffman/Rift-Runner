import { useEffect, useState, type ReactElement } from 'react'
import { getSkills, type SkillProgressResponse } from '../api/client'

interface SkillsPanelProps {
  accessToken: string
  refreshKey: number
}

interface SkillVisual {
  color: string
  colorDeep: string
  flavor: string
  icon: ReactElement
}

const SKILL_VISUALS: Record<string, SkillVisual> = {
  speed: {
    color: 'var(--gold)',
    colorDeep: 'var(--gold-deep)',
    flavor: 'Pace vs. your own history',
    icon: <polygon points="13,2 4,14 11,14 9,22 20,9 12,9" fill="#fff" />,
  },
  endurance: {
    color: 'var(--moss)',
    colorDeep: 'var(--moss-deep)',
    flavor: 'Progressive overload, not absolutes',
    icon: <polygon points="3,19 9,8 13,14 17,6 21,19" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinejoin="round" />,
  },
  health: {
    color: 'var(--coral)',
    colorDeep: 'var(--coral-deep)',
    flavor: 'Lower HR for the same effort',
    icon: (
      <path
        d="M12 20 C6 15.5 3 12 3 8.4 3 5.7 5.1 4 7.4 4 9 4 10.5 5 12 7 13.5 5 15 4 16.6 4 18.9 4 21 5.7 21 8.4 21 12 18 15.5 12 20 Z"
        fill="#fff"
      />
    ),
  },
  consistency: {
    color: 'var(--plum)',
    colorDeep: 'var(--plum-deep)',
    flavor: 'Streaks & weekly frequency',
    icon: <path d="M12 2 C9 6 8 8.5 8 11.5 8 15 9.8 17.2 12 22 14.2 17.2 16 15 16 11.5 16 8.5 15 6 12 2 Z" fill="#fff" />,
  },
  explorer: {
    color: 'var(--sky)',
    colorDeep: 'var(--sky-deep)',
    flavor: 'New courses & regions, first time only',
    icon: (
      <>
        <circle cx="12" cy="12" r="8.5" fill="none" stroke="#fff" strokeWidth="2" />
        <polygon points="15,9 12,12 9,15 12,12" fill="#fff" />
      </>
    ),
  },
}

const DEFAULT_VISUAL: SkillVisual = {
  color: 'var(--teal)',
  colorDeep: 'var(--teal-deep)',
  flavor: 'Keep training to grow this skill',
  icon: <circle cx="12" cy="12" r="7" fill="none" stroke="#fff" strokeWidth="2" />,
}

function SkillsPanel({ accessToken, refreshKey }: SkillsPanelProps) {
  const [skillList, setSkillList] = useState<SkillProgressResponse[] | null>(null)

  useEffect(() => {
    getSkills(accessToken)
      .then(setSkillList)
      .catch(() => setSkillList(null))
  }, [accessToken, refreshKey])

  if (!skillList || skillList.length === 0) return null

  return (
    <section className="section">
      <div className="section-head">
        <span className="section-title">Stats</span>
        <span className="section-sub">skills never gate your main level</span>
      </div>
      <div className="skills-grid">
        {skillList.map((skill) => {
          const visual = SKILL_VISUALS[skill.key] ?? DEFAULT_VISUAL
          const pct = Math.min(100, (skill.xp_into_level / skill.xp_to_next_level_snapshot) * 100)
          return (
            <div key={skill.key} className="skill-card" style={{ '--badge-c': visual.color, '--badge-c-deep': visual.colorDeep } as React.CSSProperties}>
              <div className="badge">
                <svg viewBox="0 0 24 24">{visual.icon}</svg>
              </div>
              <div className="skill-name">{skill.display_name}</div>
              <div className="skill-level">Level {skill.level}</div>
              <div className="skill-bar-track">
                <div className="skill-bar-fill" style={{ width: `${pct}%` }} />
              </div>
              <p className="skill-flavor">{visual.flavor}</p>
            </div>
          )
        })}
      </div>
    </section>
  )
}

export default SkillsPanel
