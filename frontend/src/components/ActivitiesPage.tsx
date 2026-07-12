import { useEffect, useState } from 'react'
import {
  deleteActivity,
  getActivities,
  getImportableActivities,
  importActivities,
  type ActivitySummaryResponse,
  type ImportableActivityResponse,
  type UserResponse,
} from '../api/client'
import { formatDateTime, formatDistance, formatDuration } from '../utils/format'
import './ActivitiesPage.css'

interface ActivitiesPageProps {
  accessToken: string
  units?: string
  refreshKey: number
  onUserUpdate: (user: UserResponse) => void
}

function ActivitiesPage({ accessToken, units, refreshKey, onUserUpdate }: ActivitiesPageProps) {
  const [activities, setActivities] = useState<ActivitySummaryResponse[] | null>(null)
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [importOpen, setImportOpen] = useState(false)
  const [importable, setImportable] = useState<ImportableActivityResponse[] | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [importLoading, setImportLoading] = useState(false)
  const [importSubmitting, setImportSubmitting] = useState(false)
  const [importError, setImportError] = useState<string | null>(null)

  const loadActivities = () => {
    getActivities(accessToken, 200)
      .then(setActivities)
      .catch(() => setActivities(null))
  }

  useEffect(loadActivities, [accessToken, refreshKey])

  const handleDelete = async (activityId: string) => {
    setError(null)
    setDeletingId(activityId)
    try {
      const updated = await deleteActivity(accessToken, activityId)
      onUserUpdate(updated)
      setPendingDeleteId(null)
      loadActivities()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete activity')
    } finally {
      setDeletingId(null)
    }
  }

  const handleOpenImport = async () => {
    setImportOpen(true)
    setImportError(null)
    setImportLoading(true)
    setSelectedIds(new Set())
    try {
      const results = await getImportableActivities(accessToken)
      setImportable(results)
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Could not reach Garmin')
      setImportable([])
    } finally {
      setImportLoading(false)
    }
  }

  const toggleSelected = (garminActivityId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(garminActivityId)) {
        next.delete(garminActivityId)
      } else {
        next.add(garminActivityId)
      }
      return next
    })
  }

  const handleImport = async () => {
    if (selectedIds.size === 0) return
    setImportError(null)
    setImportSubmitting(true)
    try {
      const updated = await importActivities(accessToken, Array.from(selectedIds))
      onUserUpdate(updated)
      setImportOpen(false)
      setImportable(null)
      loadActivities()
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Could not import the selected activities')
    } finally {
      setImportSubmitting(false)
    }
  }

  return (
    <div className="sections">
      <section className="section">
        <div className="section-head">
          <span className="section-title">Manage Activities</span>
          <span className="section-sub">delete a mistake, or bring in something from before you connected</span>
        </div>

        <div className="card activities-import-card">
          {!importOpen ? (
            <button type="button" className="btn-ghost" onClick={handleOpenImport}>
              Find activities to import
            </button>
          ) : (
            <div className="import-picker">
              <p className="import-picker-head">
                Activities Garmin has from the weeks before this account was created, not already synced here.
              </p>
              {importLoading && <p className="import-loading">Searching Garmin…</p>}
              {importError && <p className="form-error">{importError}</p>}
              {!importLoading && importable && importable.length === 0 && !importError && (
                <p className="import-empty">Nothing new found in that window.</p>
              )}
              {!importLoading && importable && importable.length > 0 && (
                <ul className="import-list">
                  {importable.map((item) => (
                    <li key={item.garmin_activity_id} className="import-row">
                      <label>
                        <input
                          type="checkbox"
                          checked={selectedIds.has(item.garmin_activity_id)}
                          onChange={() => toggleSelected(item.garmin_activity_id)}
                        />
                        <span className="import-row-name">{item.activity_name ?? item.activity_type}</span>
                        <span className="import-row-meta">
                          {formatDateTime(item.start_time)} · {formatDistance(item.distance_meters, units)} ·{' '}
                          {formatDuration(item.duration_seconds)}
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
              <div className="import-actions">
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => {
                    setImportOpen(false)
                    setImportable(null)
                  }}
                  disabled={importSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={handleImport}
                  disabled={importSubmitting || selectedIds.size === 0}
                >
                  {importSubmitting ? 'Importing…' : `Import Selected (${selectedIds.size})`}
                </button>
              </div>
            </div>
          )}
        </div>

        {error && <p className="form-error">{error}</p>}

        {activities && activities.length > 0 ? (
          <div className="activities-manage-list">
            {activities.map((activity) => (
              <div key={activity.id} className="card activities-manage-row">
                <div className="activities-manage-main">
                  <span className="activity-name">
                    {activity.activity_name ?? activity.activity_type}
                    {activity.is_personal_record && <span className="pr-badge">PR</span>}
                  </span>
                  <span className="activity-meta">
                    {formatDateTime(activity.start_time)} · {formatDistance(activity.distance_meters, units)} ·{' '}
                    {formatDuration(activity.duration_seconds)}
                  </span>
                  {activity.course_name && (
                    <span className="activity-course">
                      {activity.course_name}
                      {activity.region_name ? ` · ${activity.region_name}` : ''}
                    </span>
                  )}
                </div>
                {activity.main_xp && <span className="activity-xp">+{Math.round(activity.main_xp.final_xp)} XP</span>}

                {pendingDeleteId === activity.id ? (
                  <div className="activities-manage-confirm">
                    <button
                      type="button"
                      className="btn-ghost"
                      onClick={() => setPendingDeleteId(null)}
                      disabled={deletingId === activity.id}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="btn-danger"
                      onClick={() => handleDelete(activity.id)}
                      disabled={deletingId === activity.id}
                    >
                      {deletingId === activity.id ? 'Deleting…' : 'Delete'}
                    </button>
                  </div>
                ) : (
                  <button type="button" className="btn-ghost" onClick={() => setPendingDeleteId(activity.id)}>
                    Delete
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : (
          activities && <p className="import-empty">No activities yet.</p>
        )}
      </section>
    </div>
  )
}

export default ActivitiesPage
