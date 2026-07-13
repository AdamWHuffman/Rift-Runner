import { useEffect, useState, type FormEvent } from 'react'
import {
  completeGarminMfa,
  completeOnboarding,
  connectGarmin,
  getGoals,
  setActiveGoal,
  setHomeBase,
  type GoalResponse,
  type RegionResponse,
  type UserResponse,
} from '../api/client'
import AddressAutocomplete from './AddressAutocomplete'
import './OnboardingWizard.css'

interface OnboardingWizardProps {
  accessToken: string
  onComplete: (user: UserResponse) => void
  onLogout: () => void
}

type Step = 'welcome' | 'garmin' | 'home-base' | 'goal' | 'done'

const STEP_ORDER: Step[] = ['welcome', 'garmin', 'home-base', 'goal', 'done']

function ProgressDots({ stepIndex }: { stepIndex: number }) {
  return (
    <div className="onboarding-progress">
      {STEP_ORDER.slice(0, -1).map((s, i) => (
        <span key={s} className={`onboarding-dot${i <= stepIndex ? ' active' : ''}`} />
      ))}
    </div>
  )
}

function WelcomeStep({ onNext }: { onNext: () => void }) {
  return (
    <>
      <p className="onboarding-eyebrow">Welcome</p>
      <h2 className="onboarding-title">Health Quest</h2>
      <p className="onboarding-body">
        Your real runs and walks, gently reinterpreted as an RPG. A few quick steps and you're set — connecting
        Garmin is required, but the rest can be finished later from your dashboard.
      </p>
      <div className="onboarding-actions">
        <button type="button" className="btn" onClick={onNext}>
          Let's go
        </button>
      </div>
    </>
  )
}

function GarminStep({ accessToken, onNext }: { accessToken: string; onNext: () => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mfaSessionId, setMfaSessionId] = useState<string | null>(null)
  const [mfaCode, setMfaCode] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleConnect = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const result = await connectGarmin(accessToken, email, password)
      if (result.mfa_required && result.mfa_session_id) {
        setMfaSessionId(result.mfa_session_id)
      } else {
        onNext()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not connect to Garmin')
    } finally {
      setSubmitting(false)
    }
  }

  const handleMfaSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!mfaSessionId) return
    setError(null)
    setSubmitting(true)
    try {
      await completeGarminMfa(accessToken, mfaSessionId, mfaCode)
      onNext()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not verify MFA code')
    } finally {
      setSubmitting(false)
    }
  }

  // "I don't have a code" backs out to the connect form to retry -- Garmin
  // connection itself isn't skippable (the app doesn't do much without real
  // activity data), so this can't skip past it the way the other steps can.
  const handleMfaCancel = () => {
    setMfaSessionId(null)
    setMfaCode('')
    setError(null)
  }

  if (mfaSessionId) {
    return (
      <>
        <p className="onboarding-eyebrow">Step 1 of 3</p>
        <h2 className="onboarding-title">Enter Garmin MFA Code</h2>
        <p className="onboarding-body">
          Check your authenticator app or email for a code. If nothing arrives, Garmin may just be rate-limiting
          login attempts from this network rather than asking for real MFA — back out and wait a while before
          retrying.
        </p>
        <form onSubmit={handleMfaSubmit} className="form-card">
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
          {error && <p className="form-error">{error}</p>}
          <div className="onboarding-actions">
            <button type="button" className="btn-ghost" onClick={handleMfaCancel}>
              I don't have a code
            </button>
            <button type="submit" className="btn" disabled={submitting}>
              {submitting ? 'Verifying…' : 'Verify code'}
            </button>
          </div>
        </form>
      </>
    )
  }

  return (
    <>
      <p className="onboarding-eyebrow">Step 1 of 3</p>
      <h2 className="onboarding-title">Connect Garmin</h2>
      <p className="onboarding-body">
        Health Quest runs on your real Garmin activity data — there's no getting started without connecting
        it first.
      </p>
      <form onSubmit={handleConnect} className="form-card">
        <label>
          Garmin email
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Garmin password
          <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <p className="form-error">{error}</p>}
        <div className="onboarding-actions">
          <button type="submit" className="btn" disabled={submitting}>
            {submitting ? 'Connecting…' : 'Connect Garmin'}
          </button>
        </div>
      </form>
    </>
  )
}

function HomeBaseStep({ accessToken, onNext, onSkip }: { accessToken: string; onNext: () => void; onSkip: () => void }) {
  const [address, setAddress] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<RegionResponse | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const region = await setHomeBase(accessToken, address)
      setResult(region)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not find that address')
    } finally {
      setSubmitting(false)
    }
  }

  if (result) {
    return (
      <>
        <p className="onboarding-eyebrow">Step 2 of 3</p>
        <h2 className="onboarding-title">{result.name}</h2>
        <p className="onboarding-body">A {result.theme} region — this is where your journey begins.</p>
        <div className="onboarding-actions">
          <button type="button" className="btn" onClick={onNext}>
            Continue
          </button>
        </div>
      </>
    )
  }

  return (
    <>
      <p className="onboarding-eyebrow">Step 2 of 3</p>
      <h2 className="onboarding-title">Set Your Home Base</h2>
      <p className="onboarding-body">Tell us where you usually start from — this shapes your home region.</p>
      <form onSubmit={handleSubmit} className="form-card">
        <label>
          Home address
          <AddressAutocomplete accessToken={accessToken} value={address} onChange={setAddress} disabled={submitting} />
        </label>
        {error && <p className="form-error">{error}</p>}
        <div className="onboarding-actions">
          <button type="button" className="btn-ghost" onClick={onSkip}>
            Skip for now
          </button>
          <button type="submit" className="btn" disabled={submitting}>
            {submitting ? 'Finding…' : 'Set Home Base'}
          </button>
        </div>
      </form>
    </>
  )
}

function GoalStep({ accessToken, onNext, onSkip }: { accessToken: string; onNext: () => void; onSkip: () => void }) {
  const [goals, setGoals] = useState<GoalResponse[] | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getGoals(accessToken)
      .then(setGoals)
      .catch(() => setGoals([]))
  }, [accessToken])

  const handlePick = async (goalKey: string) => {
    setError(null)
    setSubmitting(true)
    try {
      await setActiveGoal(accessToken, goalKey)
      onNext()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not set goal')
      setSubmitting(false)
    }
  }

  return (
    <>
      <p className="onboarding-eyebrow">Step 3 of 3</p>
      <h2 className="onboarding-title">Choose Your Character Type</h2>
      <p className="onboarding-body">This shapes how future activities score XP — you can switch it later anytime.</p>
      <div className="onboarding-goals">
        {(goals ?? []).map((goal) => (
          <button
            key={goal.key}
            type="button"
            className="card goal-card"
            disabled={submitting}
            onClick={() => handlePick(goal.key)}
          >
            <span className="quest-name">{goal.display_name}</span>
            <p className="quest-desc">{goal.description}</p>
          </button>
        ))}
      </div>
      {error && <p className="form-error">{error}</p>}
      <div className="onboarding-actions">
        <button type="button" className="btn-ghost" onClick={onSkip} disabled={submitting}>
          Skip for now
        </button>
      </div>
    </>
  )
}

function DoneStep({ onFinish, finishing }: { onFinish: () => void; finishing: boolean }) {
  return (
    <>
      <p className="onboarding-eyebrow">All set</p>
      <h2 className="onboarding-title">Your quest begins now</h2>
      <p className="onboarding-body">
        Anything you skipped is waiting for you on your dashboard whenever you're ready.
      </p>
      <div className="onboarding-actions">
        <button type="button" className="btn" onClick={onFinish} disabled={finishing}>
          {finishing ? 'Entering…' : 'Enter the Quest'}
        </button>
      </div>
    </>
  )
}

function OnboardingWizard({ accessToken, onComplete, onLogout }: OnboardingWizardProps) {
  const [step, setStep] = useState<Step>('welcome')
  const [finishing, setFinishing] = useState(false)
  const stepIndex = STEP_ORDER.indexOf(step)

  const advance = () => {
    const next = STEP_ORDER[stepIndex + 1]
    if (next) setStep(next)
  }

  const finish = async () => {
    setFinishing(true)
    try {
      const updated = await completeOnboarding(accessToken)
      onComplete(updated)
    } catch {
      setFinishing(false)
    }
  }

  return (
    <div className="onboarding-overlay">
      <div className="card onboarding-card">
        <div className="onboarding-topbar">
          {step !== 'done' ? <ProgressDots stepIndex={stepIndex} /> : <span />}
          <button type="button" className="onboarding-logout" onClick={onLogout}>
            Log out
          </button>
        </div>
        {step === 'welcome' && <WelcomeStep onNext={advance} />}
        {step === 'garmin' && <GarminStep accessToken={accessToken} onNext={advance} />}
        {step === 'home-base' && <HomeBaseStep accessToken={accessToken} onNext={advance} onSkip={advance} />}
        {step === 'goal' && <GoalStep accessToken={accessToken} onNext={advance} onSkip={advance} />}
        {step === 'done' && <DoneStep onFinish={finish} finishing={finishing} />}
      </div>
    </div>
  )
}

export default OnboardingWizard
