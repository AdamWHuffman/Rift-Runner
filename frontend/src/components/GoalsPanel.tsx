import { useEffect, useState } from 'react'
import { getActiveGoal, getGoals, setActiveGoal, type GoalResponse } from '../api/client'

interface GoalsPanelProps {
  accessToken: string
}

function GoalsPanel({ accessToken }: GoalsPanelProps) {
  const [goals, setGoals] = useState<GoalResponse[] | null>(null)
  const [activeGoal, setActiveGoalState] = useState<GoalResponse | null>(null)
  const [pendingKey, setPendingKey] = useState<string | null>(null)
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

  const handlePick = (goalKey: string) => {
    setError(null)
    setPendingKey((current) => (current === goalKey ? null : goalKey))
  }

  const handleConfirm = async (goalKey: string) => {
    setError(null)
    setSwitching(true)
    try {
      const goal = await setActiveGoal(accessToken, goalKey)
      setActiveGoalState(goal)
      setPendingKey(null)
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
        <span className="section-title">Character Type</span>
        <span className="section-sub">your goal shapes how every activity scores XP — switch deliberately</span>
      </div>
      <div className="goals-list">
        {goals.map((goal) => {
          const isActive = activeGoal?.key === goal.key
          const isPending = pendingKey === goal.key
          return (
            <div
              key={goal.key}
              className={`card goal-card${isActive ? ' goal-card-active' : ''}${isPending ? ' goal-card-pending' : ''}`}
            >
              <button
                type="button"
                className="goal-card-main"
                disabled={switching || isActive}
                onClick={() => handlePick(goal.key)}
              >
                <span className="quest-name">
                  {goal.display_name}
                  {isActive && <span className="quest-current"> · current</span>}
                </span>
                <p className="quest-desc">{goal.description}</p>
              </button>

              {isPending && (
                <div className="goal-confirm">
                  <p className="goal-confirm-text">
                    Switch to {goal.display_name}? This changes how future activities score XP — past history stays
                    exactly as earned.
                  </p>
                  <div className="goal-confirm-actions">
                    <button type="button" className="btn-ghost" onClick={() => setPendingKey(null)} disabled={switching}>
                      Cancel
                    </button>
                    <button type="button" className="btn" onClick={() => handleConfirm(goal.key)} disabled={switching}>
                      {switching ? 'Switching…' : 'Confirm switch'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
      {error && <p className="form-error">{error}</p>}
    </section>
  )
}

export default GoalsPanel
