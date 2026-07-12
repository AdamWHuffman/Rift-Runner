import { useEffect, useRef, useState } from 'react'
import type { ActivitySummaryResponse } from '../api/client'
import { MULTIPLIER_LABELS, celsiusToFahrenheit, formatDateTime, formatDistance, formatDuration, formatElevation } from '../utils/format'
import './PostActivityXPScreen.css'

interface PostActivityXPScreenProps {
  activities: ActivitySummaryResponse[]
  onDone: () => void
  units?: string
}

type Stage = 'stats' | 'multipliers' | 'final'

const STATS_HOLD_MS = 1200
const MULTIPLIER_STEP_MS = 650
const TWEEN_MS = 420

function activityLabel(activity: ActivitySummaryResponse): string {
  return activity.activity_name ?? activity.activity_type
}

function targetForStage(
  stage: Stage,
  multiplierIndex: number,
  entries: [string, number][],
  baseXp: number,
  finalXp: number,
): number {
  if (stage === 'final') return finalXp
  const applied = entries.slice(0, multiplierIndex).reduce((acc, [, v]) => acc * v, 1)
  return baseXp * applied
}

function PostActivityXPScreen({ activities, onDone, units }: PostActivityXPScreenProps) {
  const [activityIndex, setActivityIndex] = useState(0)
  const [stage, setStage] = useState<Stage>('stats')
  const [multiplierIndex, setMultiplierIndex] = useState(0)
  const [show, setShow] = useState(false)
  const [displayXp, setDisplayXp] = useState(0)

  const timers = useRef<number[]>([])
  const rafRef = useRef<number | null>(null)
  const displayRef = useRef(0)

  const activity = activities[activityIndex]
  const xp = activity?.main_xp ?? null
  const multiplierEntries = (xp ? Object.entries(xp.multipliers) : []) as [string, number][]
  const leveledUp = xp ? xp.level_after > xp.level_before : false
  const target = xp ? targetForStage(stage, multiplierIndex, multiplierEntries, xp.base_xp, xp.final_xp) : 0

  const clearAllTimers = () => {
    timers.current.forEach((t) => window.clearTimeout(t))
    timers.current = []
  }

  // Sequence the stages for whichever activity is currently showing.
  useEffect(() => {
    clearAllTimers()
    setStage('stats')
    setMultiplierIndex(0)
    setShow(false)
    displayRef.current = 0
    setDisplayXp(0)
    timers.current.push(window.setTimeout(() => setShow(true), 20))

    if (!xp) {
      timers.current.push(window.setTimeout(() => setStage('final'), 20))
    } else {
      timers.current.push(window.setTimeout(() => setStage('multipliers'), STATS_HOLD_MS))
    }
    return clearAllTimers
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activityIndex])

  // Reveal multiplier rows one at a time, then move to the final total.
  useEffect(() => {
    if (stage !== 'multipliers' || !xp) return
    if (multiplierIndex >= multiplierEntries.length) {
      const t = window.setTimeout(() => setStage('final'), 350)
      timers.current.push(t)
      return () => window.clearTimeout(t)
    }
    const t = window.setTimeout(() => setMultiplierIndex((i) => i + 1), MULTIPLIER_STEP_MS)
    timers.current.push(t)
    return () => window.clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage, multiplierIndex])

  // Tween the displayed XP number toward whatever the current stage targets.
  useEffect(() => {
    if (!xp) return
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduced) {
      displayRef.current = target
      setDisplayXp(target)
      return
    }
    const from = displayRef.current
    const start = performance.now()
    if (rafRef.current) cancelAnimationFrame(rafRef.current)

    function tick(now: number) {
      const t = Math.min(1, (now - start) / TWEEN_MS)
      const eased = 1 - (1 - t) ** 3
      const value = from + (target - from) * eased
      displayRef.current = value
      setDisplayXp(value)
      if (t < 1) rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target])

  useEffect(() => clearAllTimers, [])

  if (!activity) return null

  const advance = () => {
    if (stage !== 'final') {
      clearAllTimers()
      setMultiplierIndex(multiplierEntries.length)
      setStage('final')
      return
    }
    setShow(false)
    const t = window.setTimeout(() => {
      if (activityIndex + 1 < activities.length) {
        setActivityIndex((i) => i + 1)
      } else {
        onDone()
      }
    }, 220)
    timers.current.push(t)
  }

  return (
    <div className={`postxp-overlay${show ? ' show' : ''}`} role="dialog" aria-label="Activity results" onClick={advance}>
      <div className="postxp-card">
        <p className="postxp-eyebrow">
          Activity Results{activities.length > 1 ? ` · ${activityIndex + 1}/${activities.length}` : ''}
        </p>
        <h2 className="postxp-title">{activityLabel(activity)}</h2>
        <p className="postxp-date">{formatDateTime(activity.start_time)}</p>

        <div className="postxp-stats-grid">
          <div className="postxp-stat">
            <span className="postxp-stat-v">{formatDistance(activity.distance_meters, units)}</span>
            <span className="postxp-stat-k">Distance</span>
          </div>
          <div className="postxp-stat">
            <span className="postxp-stat-v">{formatDuration(activity.duration_seconds)}</span>
            <span className="postxp-stat-k">Duration</span>
          </div>
          {activity.elevation_gain_meters > 0 && (
            <div className="postxp-stat">
              <span className="postxp-stat-v">{formatElevation(activity.elevation_gain_meters, units)}</span>
              <span className="postxp-stat-k">Elevation</span>
            </div>
          )}
          {activity.avg_hr != null && (
            <div className="postxp-stat">
              <span className="postxp-stat-v">{activity.avg_hr}</span>
              <span className="postxp-stat-k">Avg HR</span>
            </div>
          )}
          {activity.temperature_c != null && (
            <div className="postxp-stat">
              <span className="postxp-stat-v">{celsiusToFahrenheit(activity.temperature_c)}°F</span>
              <span className="postxp-stat-k">Weather</span>
            </div>
          )}
        </div>

        {xp ? (
          <div className="postxp-xp-block">
            <div className="postxp-total-row">
              <span className="postxp-total-label">{stage === 'final' ? 'Final XP' : 'Base XP'}</span>
              <span className="postxp-total-value">{Math.round(displayXp)}</span>
            </div>

            {multiplierEntries.length > 0 && (
              <div className="postxp-multiplier-list">
                {multiplierEntries.map(([key, value], i) => (
                  <div
                    key={key}
                    className={`postxp-multiplier-row${stage === 'final' || i < multiplierIndex ? ' revealed' : ''}`}
                  >
                    <span className="k">{MULTIPLIER_LABELS[key] ?? key}</span>
                    <span className="v">×{value.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            )}

            {stage === 'final' && activity.skill_xp.length > 0 && (
              <div className="postxp-skill-row">
                {activity.skill_xp.map((s) => (
                  <span className="postxp-skill-chip" key={s.skill_key}>
                    {s.skill_key} +{Math.round(s.final_xp)}
                  </span>
                ))}
              </div>
            )}

            {stage === 'final' && leveledUp && (
              <p className="postxp-levelup-hint">
                Level {xp.level_before} → {xp.level_after}!
              </p>
            )}
          </div>
        ) : (
          <p className="postxp-no-xp">No XP was recorded for this activity.</p>
        )}

        <p className="postxp-hint">{stage === 'final' ? 'tap anywhere to continue' : 'tap to skip'}</p>
      </div>
    </div>
  )
}

export default PostActivityXPScreen
