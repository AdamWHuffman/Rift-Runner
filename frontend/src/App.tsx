import { useEffect, useState } from 'react'
import './App.css'
import { API_BASE_URL, getCurrentUser, login, type LevelUpEvent, type SyncJobResponse, type UserResponse } from './api/client'
import ActivityFeed from './components/ActivityFeed'
import CoursesPanel from './components/CoursesPanel'
import GarminPanel from './components/GarminPanel'
import GoalsPanel from './components/GoalsPanel'
import HomeBasePanel from './components/HomeBasePanel'
import LevelUpCelebration from './components/LevelUpCelebration'
import LoginForm from './components/LoginForm'
import SkillsPanel from './components/SkillsPanel'
import SyncOverlay from './components/SyncOverlay'
import Toast from './components/Toast'

function App() {
  const [apiStatus, setApiStatus] = useState<'checking' | 'ok' | 'error'>('checking')
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [user, setUser] = useState<UserResponse | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [syncing, setSyncing] = useState(false)
  const [celebrationEvents, setCelebrationEvents] = useState<LevelUpEvent[]>([])
  const [toast, setToast] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((res) => (res.ok ? res.json() : Promise.reject(res)))
      .then(() => setApiStatus('ok'))
      .catch(() => setApiStatus('error'))
  }, [])

  const handleLogin = async (email: string, password: string) => {
    const tokens = await login(email, password)
    const me = await getCurrentUser(tokens.access_token)
    setAccessToken(tokens.access_token)
    setUser(me)
  }

  const handleLogout = () => {
    setAccessToken(null)
    setUser(null)
  }

  const handleSyncStart = () => {
    setSyncing(true)
  }

  const handleSyncComplete = (job: SyncJobResponse) => {
    setSyncing(false)
    if (!accessToken) return
    getCurrentUser(accessToken).then(setUser).catch(() => {})
    setRefreshKey((key) => key + 1)
    if (job.level_up_events && job.level_up_events.length > 0) {
      setCelebrationEvents(job.level_up_events)
    }
  }

  const handleSyncFailed = () => {
    setSyncing(false)
    setToast('Could not reach Garmin — showing cached data')
  }

  const xpPct = user ? Math.min(100, (user.xp_into_level / user.xp_to_next_level_snapshot) * 100) : 0

  return (
    <main className="app-shell">
      <div className="page">
        <header className="hero">
          <p className="eyebrow">
            API status: <strong>{apiStatus === 'checking' ? 'checking…' : apiStatus === 'ok' ? 'connected' : 'unreachable'}</strong>
          </p>
          <h1 className="wordmark">
            The Quest for <span className="pop">Health</span>
          </h1>
          <p className="tagline">Your real runs, gently reinterpreted. Every activity levels you up.</p>

          {user && accessToken && (
            <div className="card plaque">
              <div className="level-badge">
                <span className="num">{user.main_level}</span>
                <span className="lbl">Level</span>
              </div>
              <div className="plaque-body">
                <div className="name-line">
                  {user.display_name} <span className="home">· {user.email}</span>
                </div>
                <div className="xp-row">
                  <span>XP to next level</span>
                  <span className="val">
                    {Math.round(user.xp_into_level)} / {Math.round(user.xp_to_next_level_snapshot)}
                  </span>
                </div>
                <div className="xp-track">
                  <div className="xp-fill" style={{ width: `${xpPct}%` }} />
                </div>
                <p className="meta-line">
                  {user.activities_this_level} activities this level · {Math.round(user.main_xp_total)} lifetime XP
                </p>
              </div>
              <button type="button" className="btn-ghost" onClick={handleLogout}>
                Log out
              </button>
            </div>
          )}
        </header>

        {user && accessToken ? (
          <div className="sections">
            <HomeBasePanel accessToken={accessToken} />
            <GoalsPanel accessToken={accessToken} />
            <SkillsPanel accessToken={accessToken} refreshKey={refreshKey} />
            <CoursesPanel accessToken={accessToken} refreshKey={refreshKey} />
            <ActivityFeed accessToken={accessToken} refreshKey={refreshKey} />
            <GarminPanel
              accessToken={accessToken}
              onSyncStart={handleSyncStart}
              onSyncComplete={handleSyncComplete}
              onSyncFailed={handleSyncFailed}
            />
          </div>
        ) : (
          <LoginForm onSubmit={handleLogin} />
        )}
      </div>

      {syncing && <SyncOverlay />}
      {celebrationEvents.length > 0 && (
        <LevelUpCelebration events={celebrationEvents} onDone={() => setCelebrationEvents([])} />
      )}
      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </main>
  )
}

export default App
