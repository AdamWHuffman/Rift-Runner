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
}

function GarminPanel({ accessToken }: GarminPanelProps) {
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
        .then(setJob)
        .catch(() => {})
    }, 1200)
    return () => clearInterval(interval)
  }, [job, accessToken])

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
      const result = await triggerSync(accessToken)
      setJob(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start sync')
    }
  }

  if (status === null) {
    return <p>Loading Garmin status…</p>
  }

  if (mfaSessionId) {
    return (
      <div className="garmin-panel">
        <h2>Enter Garmin MFA code</h2>
        <form onSubmit={handleMfaSubmit} className="login-form">
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
          <button type="submit" disabled={connecting}>
            {connecting ? 'Verifying…' : 'Verify code'}
          </button>
          {error && <p className="login-error">{error}</p>}
        </form>
      </div>
    )
  }

  if (!status.connected || status.status === 'needs_reauth') {
    return (
      <div className="garmin-panel">
        <h2>Connect Garmin</h2>
        {status.status === 'needs_reauth' && (
          <p className="login-error">Your Garmin session expired — reconnect below.</p>
        )}
        <form onSubmit={handleConnect} className="login-form">
          <label>
            Garmin email
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Garmin password
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <button type="submit" disabled={connecting}>
            {connecting ? 'Connecting…' : 'Connect Garmin'}
          </button>
          {error && <p className="login-error">{error}</p>}
        </form>
      </div>
    )
  }

  const syncInFlight = job !== null && (job.status === 'queued' || job.status === 'running')

  return (
    <div className="garmin-panel">
      <h2>Garmin</h2>
      <p>Status: {status.status}</p>
      <p>Last synced: {status.last_sync_success_at ?? 'never'}</p>
      <button type="button" onClick={handleSync} disabled={syncInFlight}>
        {syncInFlight ? 'Syncing…' : 'Sync now'}
      </button>
      {job && (
        <p>
          Sync job: {job.status}
          {job.status === 'complete' && ` — ${job.activities_synced_count} activities synced`}
          {job.status === 'failed' && ` — ${job.error_message}`}
        </p>
      )}
      {error && <p className="login-error">{error}</p>}
    </div>
  )
}

export default GarminPanel
