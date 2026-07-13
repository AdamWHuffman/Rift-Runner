import { useEffect, useRef, useState } from 'react'
import type { UserResponse } from '../api/client'
import { xpProgressPct } from '../utils/format'

interface UserMenuProps {
  user: UserResponse
  onViewAccount: () => void
  onLogout: () => void
}

function UserMenu({ user, onViewAccount, onLogout }: UserMenuProps) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const xpPct = xpProgressPct(user)

  useEffect(() => {
    if (!open) return
    const handleClick = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKey)
    }
  }, [open])

  return (
    <div className="user-menu" ref={rootRef}>
      <button type="button" className="user-menu-trigger" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span className="user-menu-ring" style={{ background: `conic-gradient(var(--teal) ${xpPct}%, var(--line) 0)` }}>
          <span className="user-menu-badge">{user.main_level}</span>
        </span>
        <span className="user-menu-name">{user.display_name}</span>
      </button>

      {open && (
        <div className="user-menu-dropdown">
          <div className="user-menu-stats">
            <span className="user-menu-badge lg">{user.main_level}</span>
            <div className="user-menu-stats-body">
              <div className="user-menu-name-line">{user.display_name}</div>
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
          <div className="user-menu-divider" />
          <button
            type="button"
            className="user-menu-item"
            onClick={() => {
              setOpen(false)
              onViewAccount()
            }}
          >
            View Account
          </button>
          <button
            type="button"
            className="user-menu-item danger"
            onClick={() => {
              setOpen(false)
              onLogout()
            }}
          >
            Log out
          </button>
        </div>
      )}
    </div>
  )
}

export default UserMenu
