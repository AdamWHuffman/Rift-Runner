import { useEffect, useState } from 'react'
import { getActivities, type ActivitySummaryResponse } from '../api/client'
import { MULTIPLIER_LABELS, celsiusToFahrenheit, formatDateTime, formatDistance, formatDuration } from '../utils/format'

interface ActivityFeedProps {
  accessToken: string
  refreshKey: number
  units?: string
}

function ActivityFeed({ accessToken, refreshKey, units }: ActivityFeedProps) {
  const [activities, setActivities] = useState<ActivitySummaryResponse[] | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  useEffect(() => {
    getActivities(accessToken)
      .then(setActivities)
      .catch(() => setActivities(null))
  }, [accessToken, refreshKey])

  if (!activities || activities.length === 0) return null

  return (
    <div className="activity-feed">
      <div className="section-head">
        <span className="section-title">Activity Log</span>
        <span className="section-sub">every run, with the XP math shown in the open</span>
      </div>
      <div className="activity-list">
        {activities.map((activity) => {
          const expanded = expandedId === activity.id
          return (
            <div key={activity.id} className="activity-card card">
              <button
                type="button"
                className="activity-row"
                onClick={() => setExpandedId(expanded ? null : activity.id)}
                aria-expanded={expanded}
              >
                <div className="activity-main">
                  <span className="activity-name">
                    {activity.activity_name ?? activity.activity_type}
                    {activity.is_personal_record && <span className="pr-badge">PR</span>}
                  </span>
                  <span className="activity-meta">
                    {formatDateTime(activity.start_time)} · {formatDistance(activity.distance_meters, units)} ·{' '}
                    {formatDuration(activity.duration_seconds)}
                    {activity.avg_hr ? ` · avg HR ${activity.avg_hr}` : ''}
                    {activity.temperature_c != null ? ` · ${celsiusToFahrenheit(activity.temperature_c)}°F` : ''}
                    {activity.heat_index_c != null &&
                    Math.round(activity.heat_index_c) !== Math.round(activity.temperature_c ?? activity.heat_index_c)
                      ? ` (feels ${celsiusToFahrenheit(activity.heat_index_c)}°F)`
                      : ''}
                  </span>
                  {activity.course_name && (
                    <span className="activity-course">
                      {activity.course_name}
                      {activity.region_name ? ` · ${activity.region_name}` : ''}
                    </span>
                  )}
                </div>
                {activity.main_xp && <span className="activity-xp">+{Math.round(activity.main_xp.final_xp)} XP</span>}
                <span className="chevron">{expanded ? '−' : '+'}</span>
              </button>

              {expanded && (
                <div className="activity-breakdown">
                  {activity.main_xp ? (
                    <>
                      <div className="breakdown-row">
                        <span className="k">Base XP (effort, from HR zones)</span>
                        <span className="v">{Math.round(activity.main_xp.base_xp)}</span>
                      </div>
                      {Object.entries(activity.main_xp.multipliers).map(([key, value]) => (
                        <div className="breakdown-row" key={key}>
                          <span className="k">× {MULTIPLIER_LABELS[key] ?? key}</span>
                          <span className="v">{value.toFixed(2)}</span>
                        </div>
                      ))}
                      <div className="breakdown-row hl">
                        <span className="k">Final XP earned</span>
                        <span className="v">{Math.round(activity.main_xp.final_xp)}</span>
                      </div>
                    </>
                  ) : (
                    <p className="no-xp">No XP was recorded for this activity.</p>
                  )}
                  {activity.skill_xp.length > 0 && (
                    <div className="skill-xp-row">
                      {activity.skill_xp.map((s) => (
                        <span className="skill-xp-chip" key={s.skill_key}>
                          {s.skill_key} +{Math.round(s.final_xp)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default ActivityFeed
