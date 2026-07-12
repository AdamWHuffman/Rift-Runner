import { useEffect, useState, type FormEvent } from 'react'
import {
  completeGarminMfa,
  connectGarmin,
  getGarminStatus,
  getSyncJob,
  triggerSync,
  type GarminStatusResponse,
  type SyncJobResponse,
} from '../api/client'

interface GarminPanelProps {
  accessToken: string
  onSyncStart?: () => void
  onSyncComplete?: (job: SyncJobResponse) => void
}

function GarminPanel({ accessToken, onSyncStart, onSyncComplete }: GarminPanelProps) {
  const [status, setStatus] = useState<GarminStatusResponse | null>(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mfaSessionId, setMfaSessionId] = useState<string | null>(null)
  const [mfaCode, setMfaCode] = useState('')
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [job, setJob] = useState<SyncJobResponse | null>(null)

  const refreshStatus = () => {
    getGarminStatus(accessToken)
      .then(setStatus)
      .catch(() => setStatus(null))
  }

  useEffect(refreshStatus, [accessToken])

  useEffect(() => {
    if (!job || job.status === 'complete' || job.status === 'failed') return
    const interval = setInterval(() => {
      getSyncJob(accessToken, job.id)
        .then((updated) => {
          setJob(updated)
          if (updated.status === 'complete') onSyncComplete?.(updated)
        })
        .catch(() => {})
    }, 1200)
    return () => clearInterval(interval)
  }, [job, accessToken, onSyncComplete])

  const handleConnect = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setConnecting(true)
    try {
      const result = await connectGarmin(accessToken, email, password)
      if (result.mfa_required && result.mfa_session_id) {
        setMfaSessionId(result.mfa_session_id)
      } else {
        setPassword('')
        refreshStatus()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not connect to Garmin')
    } finally {
      setConnecting(false)
    }
  }

  const handleMfaSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!mfaSessionId) return
    setError(null)
    setConnecting(true)
    try {
      await completeGarminMfa(accessToken, mfaSessionId, mfaCode)
      setMfaSessionId(null)
      setMfaCode('')
      setPassword('')
      refreshStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not verify MFA code')
    } finally {
      setConnecting(false)
    }
  }

  const handleSync = async () => {
    setError(null)
    try {
      onSyncStart?.()
      const result = await triggerSync(accessToken)
      setJob(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start sync')
    }
  }

  if (status === null) {
    return null
  }

  if (mfaSessionId) {
    return (
      <section className="section">
        <div className="section-head">
          <span className="section-title">Enter Garmin MFA Code</span>
        </div>
        <form onSubmit={handleMfaSubmit} className="card form-card">
          <label>
            MFA code
            <input
              type="text"
              inputMode="numeric"
              required
              value={mfaCode}
              onChange={(e) => setMfaCode(e.target.value)}
              autoFocus
            />
          </label>
          <button type="submit" className="btn" disabled={connecting}>
            {connecting ? 'Verifying…' : 'Verify code'}
          </button>
          {error && <p className="form-error">{error}</p>}
        </form>
      </section>
    )
  }

  if (!status.connected || status.status === 'needs_reauth') {
    return (
      <section className="section">
        <div className="section-head">
          <span className="section-title">Connect Garmin</span>
          <span className="section-sub">sync your real activities to start earning XP</span>
        </div>
        {status.status === 'needs_reauth' && <p className="form-error">Your Garmin session expired — reconnect below.</p>}
        <form onSubmit={handleConnect} className="card form-card">
          <label>
            Garmin email
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Garmin password
            <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          <button type="submit" className="btn" disabled={connecting}>
            {connecting ? 'Connecting…' : 'Connect Garmin'}
          </button>
          {error && <p className="form-error">{error}</p>}
        </form>
      </section>
    )
  }

  const syncInFlight = job !== null && (job.status === 'queued' || job.status === 'running')

  return (
    <section className="section">
      <div className="section-head">
        <span className="section-title">Garmin</span>
        <span className="section-sub">
          {status.status} · last synced {status.last_sync_success_at ? new Date(status.last_sync_success_at).toLocaleString() : 'never'}
        </span>
      </div>
      <div className="card garmin-sync-card">
        <button type="button" className="btn" onClick={handleSync} disabled={syncInFlight}>
          {syncInFlight ? 'Syncing…' : 'Sync now'}
        </button>
        {job && (
          <p className="sync-status-line">
            {job.status === 'complete' && `${job.activities_synced_count} activities synced`}
            {job.status === 'failed' && job.error_message}
            {(job.status === 'queued' || job.status === 'running') && 'Sync in progress…'}
          </p>
        )}
        {error && <p className="form-error">{error}</p>}
      </div>
    </section>
  )
}

export default GarminPanel
