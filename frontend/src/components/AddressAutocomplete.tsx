import { useEffect, useRef, useState } from 'react'
import { getAddressSuggestions, type AddressSuggestion } from '../api/client'
import './AddressAutocomplete.css'

interface AddressAutocompleteProps {
  accessToken: string
  value: string
  onChange: (value: string) => void
  disabled?: boolean
}

const DEBOUNCE_MS = 350
const MIN_QUERY_LENGTH = 3

function AddressAutocomplete({ accessToken, value, onChange, disabled }: AddressAutocompleteProps) {
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([])
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const debounceRef = useRef<number | null>(null)

  useEffect(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current)
    if (value.trim().length < MIN_QUERY_LENGTH) {
      setSuggestions([])
      return
    }
    debounceRef.current = window.setTimeout(() => {
      getAddressSuggestions(accessToken, value)
        .then((results) => {
          setSuggestions(results)
          setOpen(results.length > 0)
        })
        .catch(() => setSuggestions([]))
    }, DEBOUNCE_MS)
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current)
    }
  }, [value, accessToken])

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (suggestion: AddressSuggestion) => {
    onChange(suggestion.display_name)
    setSuggestions([])
    setOpen(false)
  }

  return (
    <div className="address-autocomplete" ref={containerRef}>
      <input
        type="text"
        required
        autoComplete="off"
        disabled={disabled}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setOpen(suggestions.length > 0)}
      />
      {open && suggestions.length > 0 && (
        <ul className="address-suggestions">
          {suggestions.map((s) => (
            <li key={`${s.lat},${s.lon}`}>
              <button type="button" onClick={() => handleSelect(s)}>
                {s.display_name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default AddressAutocomplete
