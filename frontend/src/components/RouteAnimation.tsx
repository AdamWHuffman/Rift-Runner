import type { LatLngBoundsExpression, LatLngExpression } from 'leaflet'
import { useEffect, useRef, useState } from 'react'
import { CircleMarker, MapContainer, Polyline, TileLayer } from 'react-leaflet'
import type { LatLon } from '../api/client'
import { TILE_URL } from '../utils/mapTheme'
import FitBoundsOnMount from './FitBoundsOnMount'
import './RouteAnimation.css'

interface RouteAnimationProps {
  polyline: LatLon[]
  onComplete?: () => void
}

// A Strava-style route replay: a dot travels the real GPS path with the line
// drawing in behind it, on a map framed once (fixed, not panning) to fit the
// whole route. Deliberately built as "play the points in order, from 0 to N"
// rather than baked to exactly this activity -- the intended next step is
// threading loot waypoints into this same timeline so it can pause partway
// through and reveal a pickup before continuing, without changing the
// underlying animation mechanics.
const DURATION_MS = 3200
const HOLD_AT_END_MS = 550
const ROUTE_COLOR = '#ef7f63'

function RouteAnimation({ polyline, onComplete }: RouteAnimationProps) {
  const points: LatLngExpression[] = polyline.map((p) => [p.lat, p.lon])
  const [revealCount, setRevealCount] = useState(2)
  const rafRef = useRef<number | null>(null)

  const lats = polyline.map((p) => p.lat)
  const lons = polyline.map((p) => p.lon)
  const bounds: LatLngBoundsExpression = [
    [Math.min(...lats), Math.min(...lons)],
    [Math.max(...lats), Math.max(...lons)],
  ]

  useEffect(() => {
    let cancelled = false
    // Deliberately does NOT check prefers-reduced-motion -- unlike the
    // decorative tweens/fades elsewhere in this app, this animation is the
    // actual feature being shown, not a flourish on top of static content
    // that's equally complete without it.
    const start = performance.now()
    let holdTimer: number | null = null

    function tick(now: number) {
      const t = Math.min(1, (now - start) / DURATION_MS)
      setRevealCount(Math.max(2, Math.round(t * (points.length - 1)) + 1))
      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick)
      } else {
        holdTimer = window.setTimeout(() => {
          if (!cancelled) onComplete?.()
        }, HOLD_AT_END_MS)
      }
    }
    rafRef.current = requestAnimationFrame(tick)

    return () => {
      cancelled = true
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      if (holdTimer) window.clearTimeout(holdTimer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [polyline])

  const revealedPoints = points.slice(0, revealCount)
  const currentPoint = points[revealCount - 1]
  const inProgress = revealCount < points.length

  return (
    <div className="route-anim-wrap">
      <MapContainer
        center={points[0]}
        zoom={14}
        className="route-anim-inner"
        attributionControl={false}
        zoomControl={false}
        dragging={false}
        scrollWheelZoom={false}
        doubleClickZoom={false}
        touchZoom={false}
        boxZoom={false}
        keyboard={false}
      >
        <TileLayer url={TILE_URL} subdomains="abcd" maxZoom={19} />
        <Polyline positions={revealedPoints} pathOptions={{ color: ROUTE_COLOR, weight: 4, opacity: 0.9 }} />
        <CircleMarker
          center={points[0]}
          radius={5}
          pathOptions={{ color: '#fff', weight: 2, fillColor: ROUTE_COLOR, fillOpacity: 1 }}
        />
        {inProgress && (
          <CircleMarker center={currentPoint} radius={12} pathOptions={{ stroke: false, fillColor: ROUTE_COLOR, fillOpacity: 0.25 }} />
        )}
        <CircleMarker
          center={currentPoint}
          radius={6}
          pathOptions={{ color: '#fff', weight: 2, fillColor: ROUTE_COLOR, fillOpacity: 1 }}
        />
        <FitBoundsOnMount bounds={bounds} padding={[24, 24]} />
      </MapContainer>
    </div>
  )
}

export default RouteAnimation
