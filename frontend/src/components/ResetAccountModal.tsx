import { useState } from 'react'
import { resetAccount, type UserResponse } from '../api/client'
import './ResetAccountModal.css'

interface ResetAccountModalProps {
  accessToken: string
  onClose: () => void
  onReset: (user: UserResponse) => void
}

const CONFIRM_PHRASE = 'RESET'

function ResetAccountModal({ accessToken, onClose, onReset }: ResetAccountModalProps) {
  const [typed, setTyped] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = typed === CONFIRM_PHRASE && !submitting

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    setSubmitting(true)
    setError(null)
    try {
      const updated = await resetAccount(accessToken, typed)
      onReset(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reset account')
      setSubmitting(false)
    }
  }

  return (
    <div className="reset-modal-overlay" role="dialog" aria-modal="true" aria-label="Reset account progress" onClick={onClose}>
      <form className="card reset-modal-card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2 className="reset-modal-title">Reset your progress?</h2>
        <p className="reset-modal-body">
          This permanently deletes every activity, XP transaction, skill, and course-mastery record on your account
          and takes your main level back to 1. Your login, Garmin connection, home base, and active goal are
          unaffected.
        </p>
        <label className="reset-modal-label" htmlFor="reset-confirm-input">
          Type <strong>{CONFIRM_PHRASE}</strong> to confirm
        </label>
        <input
          id="reset-confirm-input"
          type="text"
          autoComplete="off"
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          autoFocus
        />
        {error && <p className="form-error">{error}</p>}
        <div className="reset-modal-actions">
          <button type="button" className="btn-ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button type="submit" className="btn-danger" disabled={!canSubmit}>
            {submitting ? 'Resetting…' : 'Reset my progress'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default ResetAccountModal
