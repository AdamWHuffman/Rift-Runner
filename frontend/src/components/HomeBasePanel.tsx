import { useEffect, useState, type FormEvent } from 'react'
import { getHomeBase, setHomeBase, type RegionResponse } from '../api/client'
import AddressAutocomplete from './AddressAutocomplete'

interface HomeBasePanelProps {
  accessToken: string
}

function HomeBasePanel({ accessToken }: HomeBasePanelProps) {
  const [region, setRegion] = useState<RegionResponse | null | undefined>(undefined)
  const [editing, setEditing] = useState(false)
  const [address, setAddress] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    getHomeBase(accessToken)
      .then(setRegion)
      .catch(() => setRegion(null))
  }, [accessToken])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const result = await setHomeBase(accessToken, address)
      setRegion(result)
      setEditing(false)
      setAddress('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not find that address')
    } finally {
      setSubmitting(false)
    }
  }

  if (region === undefined) return null

  if (region && !editing) {
    return (
      <section className="section">
        <div className="section-head">
          <span className="section-title">Home Base</span>
        </div>
        <div className="card home-base-card">
          <span className="quest-name">{region.name}</span>
          <p className="quest-desc">A {region.theme} region — this is where your journey begins.</p>
          <button type="button" className="btn-ghost home-base-change" onClick={() => setEditing(true)}>
            Change home base
          </button>
        </div>
      </section>
    )
  }

  return (
    <section className="section">
      <div className="section-head">
        <span className="section-title">{region ? 'Change Your Home Base' : 'Set Your Home Base'}</span>
        <span className="section-sub">tell us where you usually start from</span>
      </div>
      <form onSubmit={handleSubmit} className="card form-card">
        <label>
          Home address
          <AddressAutocomplete accessToken={accessToken} value={address} onChange={setAddress} disabled={submitting} />
        </label>
        {error && <p className="form-error">{error}</p>}
        <div className="form-actions">
          {region && (
            <button
              type="button"
              className="btn-ghost"
              onClick={() => {
                setEditing(false)
                setError(null)
              }}
              disabled={submitting}
            >
              Cancel
            </button>
          )}
          <button type="submit" className="btn" disabled={submitting}>
            {submitting ? 'Finding…' : region ? 'Update Home Base' : 'Set Home Base'}
          </button>
        </div>
      </form>
    </section>
  )
}

export default HomeBasePanel
