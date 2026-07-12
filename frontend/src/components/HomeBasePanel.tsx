import { useEffect, useState, type FormEvent } from 'react'
import { getHomeBase, setHomeBase, type RegionResponse } from '../api/client'

interface HomeBasePanelProps {
  accessToken: string
}

function HomeBasePanel({ accessToken }: HomeBasePanelProps) {
  const [region, setRegion] = useState<RegionResponse | null | undefined>(undefined)
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not find that address')
    } finally {
      setSubmitting(false)
    }
  }

  if (region === undefined) return null

  if (region) {
    return (
      <div className="home-base-panel">
        <h2>Home Base</h2>
        <p>
          <strong>{region.name}</strong> ({region.theme})
        </p>
      </div>
    )
  }

  return (
    <div className="home-base-panel">
      <h2>Set Your Home Base</h2>
      <form onSubmit={handleSubmit} className="login-form">
        <label>
          Home address
          <input type="text" required value={address} onChange={(e) => setAddress(e.target.value)} />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? 'Finding…' : 'Set Home Base'}
        </button>
        {error && <p className="login-error">{error}</p>}
      </form>
    </div>
  )
}

export default HomeBasePanel
