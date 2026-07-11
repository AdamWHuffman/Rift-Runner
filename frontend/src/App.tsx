import { useEffect, useState } from 'react'
import './App.css'
import { API_BASE_URL, getCurrentUser, login, type UserResponse } from './api/client'
import LoginForm from './components/LoginForm'

function App() {
  const [apiStatus, setApiStatus] = useState<'checking' | 'ok' | 'error'>('checking')
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [user, setUser] = useState<UserResponse | null>(null)

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
        </div>
      ) : (
        <LoginForm onSubmit={handleLogin} />
      )}
    </main>
  )
}

export default App
