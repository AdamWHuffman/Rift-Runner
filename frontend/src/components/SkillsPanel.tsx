import { useEffect, useState } from 'react'
import { getSkills, type SkillProgressResponse } from '../api/client'

interface SkillsPanelProps {
  accessToken: string
  refreshKey: number
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
    <div className="skills-panel">
      <h2>Skills</h2>
      <div className="skills-grid">
        {skillList.map((skill) => (
          <div key={skill.key} className="skill-card">
            <strong>{skill.display_name}</strong>
            <span>Level {skill.level}</span>
            <div className="xp-bar xp-bar-small">
              <div
                className="xp-bar-fill"
                style={{
                  width: `${Math.min(100, (skill.xp_into_level / skill.xp_to_next_level_snapshot) * 100)}%`,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default SkillsPanel
