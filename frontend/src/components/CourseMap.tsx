import type { LatLngBoundsExpression, LatLngExpression } from 'leaflet'
import { useEffect, useLayoutEffect, useState } from 'react'
import { CircleMarker, MapContainer, Polyline, TileLayer, useMap } from 'react-leaflet'
import type { LatLon } from '../api/client'
import './CourseMap.css'

interface CourseMapProps {
  polyline: LatLon[]
  theme: string
  courseName: string
}

// Route/marker colors keyed by the region's real theme (region_engine/geocode.py
// THEME_* constants). This is a deliberate first step toward a bigger future
// goal -- reskinning this same map with fully themed biomes -- so the palette
// intentionally reuses the app's existing design tokens rather than inventing
// a separate one-off color set.
const THEME_COLORS: Record<string, { line: string; start: string; end: string }> = {
  riverlands: { line: '#4a91a8', start: '#6fb3c9', end: '#4a91a8' },
  highlands: { line: '#7d4f8a', start: '#9b6fa8', end: '#7d4f8a' },
  greenwood: { line: '#416b40', start: '#5b8a5a', end: '#416b40' },
  metropolis: { line: '#d35f45', start: '#ef7f63', end: '#d35f45' },
}
const DEFAULT_COLORS = THEME_COLORS.greenwood

const TILE_URL = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'

function RouteLayer({ points, colors }: { points: LatLngExpression[]; colors: { line: string; start: string; end: string } }) {
  return (
    <>
      <TileLayer url={TILE_URL} subdomains="abcd" maxZoom={19} />
      <Polyline positions={points} pathOptions={{ color: colors.line, weight: 4, opacity: 0.9 }} />
      <CircleMarker center={points[0]} radius={6} pathOptions={{ color: '#fff', weight: 2, fillColor: colors.start, fillOpacity: 1 }} />
      <CircleMarker
        center={points[points.length - 1]}
        radius={6}
        pathOptions={{ color: '#fff', weight: 2, fillColor: colors.end, fillOpacity: 1 }}
      />
    </>
  )
}

// react-leaflet's declarative `bounds` prop applies fitBounds() in an effect
// that runs *after* the map's first paint at whatever placeholder view it
// started with -- the tile pane's CSS transform gets updated for the new
// view, but tiles already requested/rendered for the placeholder view can be
// left behind at their stale transform offset, producing a torn-looking
// background (the SVG route overlay is unaffected since it's positioned
// fresh from lat/lon on every render, which is why only the tiles looked
// wrong). Calling fitBounds ourselves in useLayoutEffect -- synchronously,
// before the browser paints anything -- means there's never a placeholder
// view to leave tiles behind from in the first place.
function FitBoundsOnMount({ bounds, padding }: { bounds: LatLngBoundsExpression; padding: [number, number] }) {
  const map = useMap()
  useLayoutEffect(() => {
    map.fitBounds(bounds, { padding, animate: false });
    // A follow-up invalidateSize covers the (rarer) case where the
    // container's own size wasn't final yet at layout-effect time, e.g. a
    // parent still mid CSS-transition.
    const timer = setTimeout(() => map.invalidateSize(), 250)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map])
  return null
}

function CourseMap({ polyline, theme, courseName }: CourseMapProps) {
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    if (!expanded) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setExpanded(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [expanded])

  if (!polyline || polyline.length < 2) return null

  const colors = THEME_COLORS[theme] ?? DEFAULT_COLORS
  const points: LatLngExpression[] = polyline.map((p) => [p.lat, p.lon])
  const lats = polyline.map((p) => p.lat)
  const lons = polyline.map((p) => p.lon)
  const bounds: LatLngBoundsExpression = [
    [Math.min(...lats), Math.min(...lons)],
    [Math.max(...lats), Math.max(...lons)],
  ]
  const fallbackCenter: LatLngExpression = [(Math.min(...lats) + Math.max(...lats)) / 2, (Math.min(...lons) + Math.max(...lons)) / 2]

  return (
    <>
      <button type="button" className="course-map" onClick={() => setExpanded(true)} aria-label={`View a larger map of ${courseName}`}>
        <MapContainer
          center={fallbackCenter}
          zoom={14}
          className="course-map-inner"
          attributionControl={false}
          zoomControl={false}
          dragging={false}
          scrollWheelZoom={false}
          doubleClickZoom={false}
          touchZoom={false}
          boxZoom={false}
          keyboard={false}
        >
          <RouteLayer points={points} colors={colors} />
          <FitBoundsOnMount bounds={bounds} padding={[20, 20]} />
        </MapContainer>
        <span className="course-map-expand-hint">
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path
              d="M9 3H4v5M15 3h5v5M9 21H4v-5M15 21h5v-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          View larger
        </span>
      </button>

      {expanded && (
        <div className="course-map-modal-overlay" role="dialog" aria-label={`${courseName} route map`} onClick={() => setExpanded(false)}>
          <div className="course-map-modal" onClick={(e) => e.stopPropagation()}>
            <div className="course-map-modal-head">
              <span className="course-map-modal-title">{courseName}</span>
              <button type="button" className="course-map-modal-close" onClick={() => setExpanded(false)} aria-label="Close map">
                ×
              </button>
            </div>
            <MapContainer
              center={fallbackCenter}
              zoom={14}
              className="course-map-modal-inner"
              attributionControl={false}
            >
              <RouteLayer points={points} colors={colors} />
              <FitBoundsOnMount bounds={bounds} padding={[30, 30]} />
            </MapContainer>
            <span className="course-map-attribution">
              ©{' '}
              <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">
                OpenStreetMap
              </a>{' '}
              · ©{' '}
              <a href="https://carto.com/attributions" target="_blank" rel="noreferrer">
                CARTO
              </a>
            </span>
          </div>
        </div>
      )}
    </>
  )
}

export default CourseMap
