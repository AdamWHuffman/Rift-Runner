import { useState } from 'react'
import type { UserResponse } from '../api/client'
import { xpProgressPct } from '../utils/format'
import GoalsPanel from './GoalsPanel'
import HomeBasePanel from './HomeBasePanel'
import ResetAccountModal from './ResetAccountModal'
import SkillsPanel from './SkillsPanel'

interface AccountPageProps {
  user: UserResponse
  accessToken: string
  refreshKey: number
  onAccountReset: (user: UserResponse) => void
}

function AccountPage({ user, accessToken, refreshKey, onAccountReset }: AccountPageProps) {
  const [resetModalOpen, setResetModalOpen] = useState(false)
  const xpPct = xpProgressPct(user)

  return (
    <div className="sections">
      <section className="section">
        <div className="card account-header">
          <div className="level-badge">
            <span className="num">{user.main_level}</span>
            <span className="lbl">Level</span>
          </div>
          <div className="account-header-body">
            <div className="account-header-name">
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
        </div>
      </section>

      <HomeBasePanel accessToken={accessToken} />
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
