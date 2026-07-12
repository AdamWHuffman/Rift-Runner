import { useEffect, useState } from 'react'
import { getActiveGoal, getGoals, setActiveGoal, type GoalResponse } from '../api/client'

interface GoalsPanelProps {
  accessToken: string
}

function GoalsPanel({ accessToken }: GoalsPanelProps) {
  const [goals, setGoals] = useState<GoalResponse[] | null>(null)
  const [activeGoal, setActiveGoalState] = useState<GoalResponse | null>(null)
  const [switching, setSwitching] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getGoals(accessToken)
      .then(setGoals)
      .catch(() => setGoals(null))
    getActiveGoal(accessToken)
      .then(setActiveGoalState)
      .catch(() => setActiveGoalState(null))
  }, [accessToken])

  const handleSelect = async (goalKey: string) => {
    setError(null)
    setSwitching(true)
    try {
      const goal = await setActiveGoal(accessToken, goalKey)
      setActiveGoalState(goal)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not set goal')
    } finally {
      setSwitching(false)
    }
  }

  if (!goals || goals.length === 0) return null

  return (
    <section className="section">
      <div className="section-head">
        <span className="section-title">Active Quest</span>
        <span className="section-sub">switch anytime — history stays intact</span>
      </div>
      <div className="goals-list">
        {goals.map((goal) => (
          <button
            key={goal.key}
            type="button"
            className={`card goal-card${activeGoal?.key === goal.key ? ' goal-card-active' : ''}`}
            disabled={switching}
            onClick={() => handleSelect(goal.key)}
          >
            <span className="quest-name">{goal.display_name}</span>
            <p className="quest-desc">{goal.description}</p>
          </button>
        ))}
      </div>
      {error && <p className="form-error">{error}</p>}
    </section>
  )
}

export default GoalsPanel
