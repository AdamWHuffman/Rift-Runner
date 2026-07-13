import type { LatLngBoundsExpression, LatLngExpression } from 'leaflet'
import { useEffect, useState } from 'react'
import { CircleMarker, MapContainer, Polyline, TileLayer } from 'react-leaflet'
import type { LatLon } from '../api/client'
import { DEFAULT_COLORS, THEME_COLORS, TILE_URL } from '../utils/mapTheme'
import './CourseMap.css'
import FitBoundsOnMount from './FitBoundsOnMount'

interface CourseMapProps {
  polyline: LatLon[]
  theme: string
  courseName: string
}

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
