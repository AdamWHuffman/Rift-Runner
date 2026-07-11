import { useEffect, useState } from 'react'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

function App() {
  const [apiStatus, setApiStatus] = useState<'checking' | 'ok' | 'error'>('checking')

  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((res) => (res.ok ? res.json() : Promise.reject(res)))
      .then(() => setApiStatus('ok'))
      .catch(() => setApiStatus('error'))
  }, [])

  return (
    <main className="app-shell">
      <h1>The Quest for Health</h1>
      <p>
        API status:{' '}
        <strong>
          {apiStatus === 'checking' ? 'checking…' : apiStatus === 'ok' ? 'connected' : 'unreachable'}
        </strong>
      </p>
    </main>
  )
}

export default App
