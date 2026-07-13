import type { LatLngBoundsExpression, LatLngExpression } from 'leaflet'
import { Fragment, useEffect, useState } from 'react'
import { Circle, CircleMarker, MapContainer, Polyline, Popup, TileLayer } from 'react-leaflet'
import { getCourses, getHomeBase, type CourseProgressResponse, type RegionResponse } from '../api/client'
import { haversineMiles } from '../utils/geo'
import { DEFAULT_COLORS, THEME_COLORS, TILE_URL } from '../utils/mapTheme'
import FitBoundsOnMount from './FitBoundsOnMount'
import './WorldMap.css'

interface WorldMapProps {
  accessToken: string
  refreshKey: number
  onNavigateToAccount: () => void
}

// The "world" boundary isn't a fixed distance -- it's sized to the farthest
// course a user has actually run, plus a little breathing room, so the
// circle always roughly tracks how far someone's real explored range is
// rather than an arbitrary guess. Purely a frontend display concept for now
// (not stored server-side). This is deliberately the surface the next phase
// (themed regions, landmarks, run-through loot) will build on top of.
const WORLD_RADIUS_BUFFER_MILES = 2
const MILES_TO_METERS = 1609.344
const HOME_COLOR = '#e8a63c'

function WorldMap({ accessToken, refreshKey, onNavigateToAccount }: WorldMapProps) {
  const [homeBase, setHomeBase] = useState<RegionResponse | null | undefined>(undefined)
  const [courses, setCourses] = useState<CourseProgressResponse[] | null>(null)

  useEffect(() => {
    getHomeBase(accessToken)
      .then(setHomeBase)
      .catch(() => setHomeBase(null))
    getCourses(accessToken)
      .then(setCourses)
      .catch(() => setCourses([]))
  }, [accessToken, refreshKey])

  if (homeBase === undefined) return null

  if (homeBase === null) {
    return (
      <div className="world-map-empty">
        <div className="card world-map-empty-card">
          <span className="section-title">Set Your Home Base First</span>
          <p className="quest-desc">Your world map is centered on your home base — set one to see it.</p>
          <button type="button" className="btn" onClick={onNavigateToAccount}>
            Go to Account
          </button>
        </div>
      </div>
    )
  }

  const home: LatLngExpression = [homeBase.centroid_lat, homeBase.centroid_lon]
  const routedCourses = (courses ?? []).filter((c) => c.polyline.length >= 2)

  // Radius = distance to the farthest course point from home, plus a
  // buffer -- the boundary hugs the user's real explored range instead of
  // an arbitrary fixed number.
  const farthestCourseMiles = routedCourses.length
    ? Math.max(
        ...routedCourses.flatMap((c) =>
          c.polyline.map((p) => haversineMiles(homeBase.centroid_lat, homeBase.centroid_lon, p.lat, p.lon)),
        ),
      )
    : 0
  const worldRadiusMiles = farthestCourseMiles + WORLD_RADIUS_BUFFER_MILES

  // Rough degrees-per-mile at this latitude, just to size the initial
  // fitBounds -- doesn't need to be precise, fitBounds' own padding covers
  // the slack. The world-radius circle already contains every course point
  // by construction (worldRadiusMiles >= farthestCourseMiles), so fitting to
  // just the circle's bounding box is sufficient -- no need to separately
  // union in each course's raw lat/lon extent.
  const milesToLatDegrees = worldRadiusMiles / 69
  const milesToLonDegrees = worldRadiusMiles / (69 * Math.cos((homeBase.centroid_lat * Math.PI) / 180))
  const bounds: LatLngBoundsExpression = [
    [homeBase.centroid_lat - milesToLatDegrees, homeBase.centroid_lon - milesToLonDegrees],
    [homeBase.centroid_lat + milesToLatDegrees, homeBase.centroid_lon + milesToLonDegrees],
  ]

  return (
    <div className="world-map-wrap">
      <MapContainer center={home} zoom={11} className="world-map-inner">
        <TileLayer url={TILE_URL} subdomains="abcd" maxZoom={19} />

        <Circle
          center={home}
          radius={worldRadiusMiles * MILES_TO_METERS}
          pathOptions={{ color: HOME_COLOR, weight: 1.5, dashArray: '6 8', fillColor: HOME_COLOR, fillOpacity: 0.04 }}
        />

        <CircleMarker center={home} radius={10} pathOptions={{ color: '#fff', weight: 3, fillColor: HOME_COLOR, fillOpacity: 1 }}>
          <Popup>
            <strong>Home Base</strong>
            <br />
            {homeBase.name}
          </Popup>
        </CircleMarker>

        {routedCourses.map((course) => {
          const colors = THEME_COLORS[course.region_theme] ?? DEFAULT_COLORS
          const points: LatLngExpression[] = course.polyline.map((p) => [p.lat, p.lon])
          return (
            <Fragment key={course.course_id}>
              <Polyline positions={points} pathOptions={{ color: colors.line, weight: 3, opacity: 0.85 }} />
              <CircleMarker center={points[0]} radius={7} pathOptions={{ color: '#fff', weight: 2, fillColor: colors.start, fillOpacity: 1 }}>
                <Popup>
                  <strong>{course.name}</strong>
                  <br />
                  {course.region_name}
                  <br />
                  Mastery Level {course.level} · Difficulty {course.difficulty_rating}
                </Popup>
              </CircleMarker>
            </Fragment>
          )
        })}

        <FitBoundsOnMount bounds={bounds} padding={[30, 30]} />
      </MapContainer>
    </div>
  )
}

export default WorldMap
