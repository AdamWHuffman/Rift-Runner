import { useEffect, useRef, useState } from 'react'
import './App.css'
import { API_BASE_URL, getCurrentUser, login, logout, refreshAccessToken, register, type ActivitySummaryResponse, type LevelUpEvent, type SyncJobResponse, type UserResponse } from './api/client'
import AccountPage from './components/AccountPage'
import ActivitiesPage from './components/ActivitiesPage'
import CoursesPanel from './components/CoursesPanel'
import GarminPanel from './components/GarminPanel'
import LevelUpCelebration from './components/LevelUpCelebration'
import LoginForm from './components/LoginForm'
import OnboardingWizard from './components/OnboardingWizard'
import PostActivityXPScreen from './components/PostActivityXPScreen'
import Toast from './components/Toast'
import UserMenu from './components/UserMenu'
import WorldMap from './components/WorldMap'

type View = 'courses' | 'activities' | 'map' | 'account'

const VIEWS: View[] = ['courses', 'activities', 'map', 'account']

function viewFromHash(): View {
  const hash = window.location.hash.slice(1)
  return (VIEWS as string[]).includes(hash) ? (hash as View) : 'activities'
}

function App() {
  const [apiStatus, setApiStatus] = useState<'checking' | 'ok' | 'error'>('checking')
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [user, setUser] = useState<UserResponse | null>(null)
  const [checkingSession, setCheckingSession] = useState(true)
  const [view, setViewState] = useState<View>(viewFromHash)
  const [refreshKey, setRefreshKey] = useState(0)
  const [syncNonce, setSyncNonce] = useState(0)
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

  // Keeps the active tab in the URL hash so a refresh (or the browser's
  // back/forward) lands back on the same tab instead of always resetting to
  // the default view.
  useEffect(() => {
    const handleHashChange = () => setViewState(viewFromHash())
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  const setView = (next: View) => {
    setViewState(next)
    if (window.location.hash.slice(1) !== next) window.location.hash = next
  }

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

  const handleRegister = async (email: string, password: string, displayName: string) => {
    const tokens = await register(email, password, displayName)
    const me = await getCurrentUser(tokens.access_token)
    setAccessToken(tokens.access_token)
    setUser(me)
  }

  const handleLogout = () => {
    logout().catch(() => {})
    setAccessToken(null)
    setUser(null)
    setView('activities')
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
    // A reset with nothing to re-sync afterward would just look broken --
    // the whole point is watching it repopulate, not needing to know a page
    // reload will restart auto-sync.
    setSyncNonce((n) => n + 1)
  }

  const handleActivitiesChanged = (updated: UserResponse) => {
    setUser(updated)
    setRefreshKey((key) => key + 1)
  }

  // Re-shows the XP reveal for an already-synced activity, purely for
  // review -- no celebration chaining afterward, since nothing new actually
  // happened (that already played out the first time this activity synced).
  const handleReplayActivity = (activity: ActivitySummaryResponse) => {
    pendingCelebrationRef.current = []
    setPostActivityQueue([activity])
  }

  const needsOnboarding = user !== null && !user.onboarding_completed_at
  const showTopbar = user !== null && accessToken !== null && !needsOnboarding

  return (
    <main className="app-shell">
      {showTopbar && (
        <header className="topbar">
          <div className="topbar-inner">
            <div className="topbar-brand">
              <span className="topbar-logo">
                Health <span className="pop">Quest</span>
              </span>
              <span className="topbar-status">
                API {apiStatus === 'checking' ? 'checking…' : apiStatus === 'ok' ? 'connected' : 'unreachable'}
              </span>
            </div>
            <nav className="app-nav">
              <button
                type="button"
                className={`app-nav-tab${view === 'courses' ? ' active' : ''}`}
                onClick={() => setView('courses')}
              >
                Courses
              </button>
              <button
                type="button"
                className={`app-nav-tab${view === 'activities' ? ' active' : ''}`}
                onClick={() => setView('activities')}
              >
                Activities
              </button>
              <button
                type="button"
                className={`app-nav-tab${view === 'map' ? ' active' : ''}`}
                onClick={() => setView('map')}
              >
                Map
              </button>
            </nav>
            <UserMenu user={user} onViewAccount={() => setView('account')} onLogout={handleLogout} />
          </div>
        </header>
      )}

      {/* Hidden (not unmounted) rather than skipped outright when the Map tab
          is active -- GarminPanel lives inside this tree and must stay
          mounted across every view switch, map included, see the comment
          below. Actually hiding the whole narrow column also keeps the
          full-bleed map from getting an empty padded gap above it. */}
      <div className="page" style={showTopbar && view === 'map' ? { display: 'none' } : undefined}>
        {!showTopbar && (
          <header className="hero">
            <p className="eyebrow">
              API status: <strong>{apiStatus === 'checking' ? 'checking…' : apiStatus === 'ok' ? 'connected' : 'unreachable'}</strong>
            </p>
            <h1 className="wordmark">
              Health <span className="pop">Quest</span>
            </h1>
            <p className="tagline">Your real runs, gently reinterpreted. Every activity levels you up.</p>
          </header>
        )}

        {checkingSession ? null : user && accessToken ? (
          needsOnboarding ? (
            <OnboardingWizard accessToken={accessToken} onComplete={setUser} onLogout={handleLogout} />
          ) : (
            <>
              {/* Kept mounted (just hidden) across view switches -- GarminPanel
                  owns in-flight sync tracking (auto-sync-on-mount, polling), and
                  unmounting it mid-sync orphaned that state, leaving syncs stuck
                  forever. Its Connect Garmin / reconnect UI conceptually lives on
                  the Account page, so it's tied to that view's visibility. */}
              <div className="sections" style={view === 'account' ? undefined : { display: 'none' }}>
                <GarminPanel
                  accessToken={accessToken}
                  syncNonce={syncNonce}
                  onSyncComplete={handleSyncComplete}
                  onSyncFailed={handleSyncFailed}
                />
              </div>
              {view === 'account' && (
                <AccountPage
                  user={user}
                  accessToken={accessToken}
                  refreshKey={refreshKey}
                  onAccountReset={handleAccountReset}
                />
              )}
              {view === 'courses' && <CoursesPanel accessToken={accessToken} refreshKey={refreshKey} />}
              {view === 'activities' && (
                <ActivitiesPage
                  accessToken={accessToken}
                  units={user.units}
                  refreshKey={refreshKey}
                  onUserUpdate={handleActivitiesChanged}
                  onReplay={handleReplayActivity}
                />
              )}
            </>
          )
        ) : (
          <LoginForm onSubmit={handleLogin} onRegister={handleRegister} />
        )}
      </div>

      {showTopbar && view === 'map' && accessToken && (
        <div className="map-page">
          <WorldMap accessToken={accessToken} refreshKey={refreshKey} onNavigateToAccount={() => setView('account')} />
        </div>
      )}

      {postActivityQueue.length > 0 && (
        <PostActivityXPScreen activities={postActivityQueue} onDone={handlePostActivityDone} units={user?.units} />
      )}
      {celebrationEvents.length > 0 && (
        <LevelUpCelebration events={celebrationEvents} onDone={() => setCelebrationEvents([])} />
      )}
      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </main>
  )
}

export default App
