import { useState } from 'react'
import type { UserResponse } from '../api/client'
import GoalsPanel from './GoalsPanel'
import ResetAccountModal from './ResetAccountModal'
import SkillsPanel from './SkillsPanel'

interface AccountPageProps {
  accessToken: string
  refreshKey: number
  onAccountReset: (user: UserResponse) => void
}

function AccountPage({ accessToken, refreshKey, onAccountReset }: AccountPageProps) {
  const [resetModalOpen, setResetModalOpen] = useState(false)

  return (
    <div className="sections">
      <SkillsPanel accessToken={accessToken} refreshKey={refreshKey} />
      <GoalsPanel accessToken={accessToken} />

      <section className="section">
        <div className="section-head">
          <span className="section-title">Danger Zone</span>
          <span className="section-sub">start over, on purpose</span>
        </div>
        <div className="card danger-zone">
          <p className="danger-zone-text">
            Reset your progress: main level, XP, skills, and every activity are wiped. Your Garmin connection, home
            base, and active goal stay put. This can't be undone.
          </p>
          <button type="button" className="btn-danger" onClick={() => setResetModalOpen(true)}>
            Reset my progress
          </button>
        </div>
      </section>

      {resetModalOpen && (
        <ResetAccountModal
          accessToken={accessToken}
          onClose={() => setResetModalOpen(false)}
          onReset={(user) => {
            setResetModalOpen(false)
            onAccountReset(user)
          }}
        />
      )}
    </div>
  )
}

export default AccountPage
