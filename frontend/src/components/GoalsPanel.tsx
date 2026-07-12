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
    <div className="goals-panel">
      <h2>Goal</h2>
      <div className="goals-list">
        {goals.map((goal) => (
          <button
            key={goal.key}
            type="button"
            className={`goal-card${activeGoal?.key === goal.key ? ' goal-card-active' : ''}`}
            disabled={switching}
            onClick={() => handleSelect(goal.key)}
          >
            <strong>{goal.display_name}</strong>
            <span className="goal-description">{goal.description}</span>
          </button>
        ))}
      </div>
      {error && <p className="login-error">{error}</p>}
    </div>
  )
}

export default GoalsPanel
