import type { LatLngBoundsExpression, LatLngExpression } from 'leaflet'
import { CircleMarker, MapContainer, Polyline, TileLayer } from 'react-leaflet'
import type { LatLon } from '../api/client'
import './CourseMap.css'

interface CourseMapProps {
  polyline: LatLon[]
  theme: string
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

function CourseMap({ polyline, theme }: CourseMapProps) {
  if (!polyline || polyline.length < 2) return null

  const colors = THEME_COLORS[theme] ?? DEFAULT_COLORS
  const points: LatLngExpression[] = polyline.map((p) => [p.lat, p.lon])
  const lats = polyline.map((p) => p.lat)
  const lons = polyline.map((p) => p.lon)
  const bounds: LatLngBoundsExpression = [
    [Math.min(...lats), Math.min(...lons)],
    [Math.max(...lats), Math.max(...lons)],
  ]

  return (
    <div className="course-map">
      <MapContainer
        bounds={bounds}
        boundsOptions={{ padding: [20, 20] }}
        scrollWheelZoom={false}
        className="course-map-inner"
        attributionControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          subdomains="abcd"
          maxZoom={19}
        />
        <Polyline positions={points} pathOptions={{ color: colors.line, weight: 4, opacity: 0.9 }} />
        <CircleMarker
          center={points[0]}
          radius={6}
          pathOptions={{ color: '#fff', weight: 2, fillColor: colors.start, fillOpacity: 1 }}
        />
        <CircleMarker
          center={points[points.length - 1]}
          radius={6}
          pathOptions={{ color: '#fff', weight: 2, fillColor: colors.end, fillOpacity: 1 }}
        />
      </MapContainer>
      <span className="course-map-attribution">
        © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> · ©{' '}
        <a href="https://carto.com/attributions" target="_blank" rel="noreferrer">CARTO</a>
      </span>
    </div>
  )
}

export default CourseMap
