import './SyncOverlay.css'

function SyncOverlay() {
  return (
    <div className="sync-overlay" role="status" aria-live="polite">
      <div className="sync-card">
        <div className="sync-spinner">
          <svg viewBox="0 0 60 60">
            <circle cx="30" cy="30" r="24" fill="none" stroke="var(--paper-soft)" strokeWidth="7" />
            <circle className="sync-arc" cx="30" cy="30" r="24" fill="none" stroke="var(--gold)" strokeWidth="7" strokeLinecap="round" />
          </svg>
        </div>
        <p className="sync-title">Syncing your adventures&hellip;</p>
        <p className="sync-sub">Fetching new activities and tallying XP</p>
      </div>
    </div>
  )
}

export default SyncOverlay
