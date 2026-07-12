import { useState, type FormEvent } from 'react'

interface LoginFormProps {
  onSubmit: (email: string, password: string) => Promise<void>
  onRegister: (email: string, password: string, displayName: string) => Promise<void>
}

function LoginForm({ onSubmit, onRegister }: LoginFormProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const switchMode = (next: 'login' | 'register') => {
    setMode(next)
    setError(null)
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      if (mode === 'register') {
        await onRegister(email, password, displayName)
      } else {
        await onSubmit(email, password)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : mode === 'register' ? 'Could not create account' : 'Login failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="login-card">
      <div className="app-nav login-mode-nav">
        <button type="button" className={`app-nav-tab${mode === 'login' ? ' active' : ''}`} onClick={() => switchMode('login')}>
          Log In
        </button>
        <button type="button" className={`app-nav-tab${mode === 'register' ? ' active' : ''}`} onClick={() => switchMode('register')}>
          Sign Up
        </button>
      </div>
      <form onSubmit={handleSubmit} className="card form-card">
        {mode === 'register' && (
          <label>
            Display name
            <input type="text" required value={displayName} onChange={(e) => setDisplayName(e.target.value)} autoComplete="name" />
          </label>
        )}
        <label>
          Email
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            minLength={mode === 'register' ? 8 : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
          />
        </label>
        <button type="submit" className="btn" disabled={submitting}>
          {submitting ? (mode === 'register' ? 'Creating account…' : 'Logging in…') : mode === 'register' ? 'Create Account' : 'Log in'}
        </button>
        {error && <p className="form-error">{error}</p>}
      </form>
    </div>
  )
}

export default LoginForm
