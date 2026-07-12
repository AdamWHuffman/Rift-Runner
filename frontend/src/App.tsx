import { useEffect, useState } from 'react'
import './App.css'
import { API_BASE_URL, getCurrentUser, login, type UserResponse } from './api/client'
import CoursesPanel from './components/CoursesPanel'
import GarminPanel from './components/GarminPanel'
import HomeBasePanel from './components/HomeBasePanel'
import LoginForm from './components/LoginForm'
import SkillsPanel from './components/SkillsPanel'

function App() {
  const [apiStatus, setApiStatus] = useState<'checking' | 'ok' | 'error'>('checking')
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [user, setUser] = useState<UserResponse | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

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

  const handleSyncComplete = () => {
    if (!accessToken) return
    getCurrentUser(accessToken).then(setUser).catch(() => {})
    setRefreshKey((key) => key + 1)
  }

  return (
    <main className="app-shell">
      <h1>The Quest for Health</h1>
      <p>
        API status:{' '}
        <strong>
          {apiStatus === 'checking' ? 'checking…' : apiStatus === 'ok' ? 'connected' : 'unreachable'}
        </strong>
      </p>

      {user && accessToken ? (
        <div>
          <p>
            Logged in as <strong>{user.display_name}</strong> ({user.email})
          </p>
          <button type="button" onClick={handleLogout}>
            Log out
          </button>

          <div className="level-panel">
            <h2>Level {user.main_level}</h2>
            <p>
              {Math.round(user.xp_into_level)} / {Math.round(user.xp_to_next_level_snapshot)} XP to next level
            </p>
            <div className="xp-bar">
              <div
                className="xp-bar-fill"
                style={{
                  width: `${Math.min(100, (user.xp_into_level / user.xp_to_next_level_snapshot) * 100)}%`,
                }}
              />
            </div>
            <p>
              {user.activities_this_level} activities this level · {Math.round(user.main_xp_total)} total XP earned
            </p>
          </div>

          <HomeBasePanel accessToken={accessToken} />

          <SkillsPanel accessToken={accessToken} refreshKey={refreshKey} />

          <CoursesPanel accessToken={accessToken} refreshKey={refreshKey} />

          <GarminPanel accessToken={accessToken} onSyncComplete={handleSyncComplete} />
        </div>
      ) : (
        <LoginForm onSubmit={handleLogin} />
      )}
    </main>
  )
}

export default App
