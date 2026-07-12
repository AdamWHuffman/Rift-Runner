import { useEffect, useRef, useState } from 'react'
import './App.css'
import { API_BASE_URL, getCurrentUser, login, logout, refreshAccessToken, type ActivitySummaryResponse, type LevelUpEvent, type SyncJobResponse, type UserResponse } from './api/client'
import AccountPage from './components/AccountPage'
import ActivityFeed from './components/ActivityFeed'
import CoursesPanel from './components/CoursesPanel'
import GarminPanel from './components/GarminPanel'
import HomeBasePanel from './components/HomeBasePanel'
import LevelUpCelebration from './components/LevelUpCelebration'
import LoginForm from './components/LoginForm'
import PostActivityXPScreen from './components/PostActivityXPScreen'
import Toast from './components/Toast'

type View = 'dashboard' | 'account'

function App() {
  const [apiStatus, setApiStatus] = useState<'checking' | 'ok' | 'error'>('checking')
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [user, setUser] = useState<UserResponse | null>(null)
  const [checkingSession, setCheckingSession] = useState(true)
  const [view, setView] = useState<View>('dashboard')
  const [refreshKey, setRefreshKey] = useState(0)
  const [postActivityQueue, setPostActivityQueue] = useState<ActivitySummaryResponse[]>([])
  const [celebrationEvents, setCelebrationEvents] = useState<LevelUpEvent[]>([])
  const [toast, setToast] = useState<string | null>(null)
  const pendingCelebrationRef = useRef<LevelUpEvent[]>([])

  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((res) => (res.ok ? res.json() : Promise.reject(res)))
      .then(() => setApiStatus('ok'))
      .catch(() => setApiStatus('error'))
  }, [])

  // Restore a session on page load/refresh from the httpOnly refresh_token
  // cookie the backend already sets on login -- without this, every reload
  // silently signs the user out even though the cookie is still valid.
  useEffect(() => {
    refreshAccessToken()
      .then(async (tokens) => {
        const me = await getCurrentUser(tokens.access_token)
        setAccessToken(tokens.access_token)
        setUser(me)
      })
      .catch(() => {})
      .finally(() => setCheckingSession(false))
  }, [])

  const handleLogin = async (email: string, password: string) => {
    const tokens = await login(email, password)
    const me = await getCurrentUser(tokens.access_token)
    setAccessToken(tokens.access_token)
    setUser(me)
  }

  const handleLogout = () => {
    logout().catch(() => {})
    setAccessToken(null)
    setUser(null)
    setView('dashboard')
  }

  const handleSyncComplete = (job: SyncJobResponse) => {
    if (!accessToken) return
    getCurrentUser(accessToken).then(setUser).catch(() => {})
    setRefreshKey((key) => key + 1)

    const newActivities = job.new_activities ?? []
    const levelUps = job.level_up_events ?? []

    if (newActivities.length > 0) {
      // Show the per-activity XP reveal first; any level-up celebration for
      // this sync is held until that finishes so the two overlays never stack.
      pendingCelebrationRef.current = levelUps
      setPostActivityQueue(newActivities)
    } else if (levelUps.length > 0) {
      setCelebrationEvents(levelUps)
    }
  }

  const handlePostActivityDone = () => {
    setPostActivityQueue([])
    if (pendingCelebrationRef.current.length > 0) {
      setCelebrationEvents(pendingCelebrationRef.current)
      pendingCelebrationRef.current = []
    }
  }

  const handleSyncFailed = () => {
    setToast('Could not reach Garmin — showing cached data')
  }

  const handleAccountReset = (updated: UserResponse) => {
    setUser(updated)
    setRefreshKey((key) => key + 1)
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
            <>
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

              <nav className="app-nav">
                <button
                  type="button"
                  className={`app-nav-tab${view === 'dashboard' ? ' active' : ''}`}
                  onClick={() => setView('dashboard')}
                >
                  Dashboard
                </button>
                <button
                  type="button"
                  className={`app-nav-tab${view === 'account' ? ' active' : ''}`}
                  onClick={() => setView('account')}
                >
                  Account
                </button>
              </nav>
            </>
          )}
        </header>

        {checkingSession ? null : user && accessToken ? (
          <>
            {/* Kept mounted (just hidden) across view switches -- GarminPanel
                owns in-flight sync tracking (auto-sync-on-mount, polling), and
                unmounting it mid-sync orphaned that state, leaving syncs stuck
                forever. */}
            <div className="sections dashboard-sections" style={view === 'dashboard' ? undefined : { display: 'none' }}>
              <HomeBasePanel accessToken={accessToken} />
              <CoursesPanel accessToken={accessToken} refreshKey={refreshKey} />
              <ActivityFeed accessToken={accessToken} refreshKey={refreshKey} />
              <GarminPanel accessToken={accessToken} onSyncComplete={handleSyncComplete} onSyncFailed={handleSyncFailed} />
            </div>
            {view === 'account' && (
              <AccountPage accessToken={accessToken} refreshKey={refreshKey} onAccountReset={handleAccountReset} />
            )}
          </>
        ) : (
          <LoginForm onSubmit={handleLogin} />
        )}
      </div>

      {postActivityQueue.length > 0 && (
        <PostActivityXPScreen activities={postActivityQueue} onDone={handlePostActivityDone} />
      )}
      {celebrationEvents.length > 0 && (
        <LevelUpCelebration events={celebrationEvents} onDone={() => setCelebrationEvents([])} />
      )}
      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </main>
  )
}

export default App
