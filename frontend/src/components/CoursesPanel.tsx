import { useEffect, useState } from 'react'
import { getCourses, type CourseProgressResponse } from '../api/client'
import CourseMap from './CourseMap'

interface CoursesPanelProps {
  accessToken: string
  refreshKey: number
}

function groupByRegion(courses: CourseProgressResponse[]): Map<string, CourseProgressResponse[]> {
  const groups = new Map<string, CourseProgressResponse[]>()
  for (const course of courses) {
    const key = course.region_name
    const list = groups.get(key)
    if (list) {
      list.push(course)
    } else {
      groups.set(key, [course])
    }
  }
  return groups
}

function CoursesPanel({ accessToken, refreshKey }: CoursesPanelProps) {
  const [courses, setCourses] = useState<CourseProgressResponse[] | null>(null)

  useEffect(() => {
    getCourses(accessToken)
      .then(setCourses)
      .catch(() => setCourses(null))
  }, [accessToken, refreshKey])

  if (!courses || courses.length === 0) return null

  const regions = groupByRegion(courses)

  return (
    <section className="section">
      <div className="section-head">
        <span className="section-title">Courses</span>
        <span className="section-sub">your routes, grouped by the region they belong to</span>
      </div>
      <div className="card region-list">
        {Array.from(regions.entries()).map(([regionName, regionCourses]) => (
          <div className="region-block" key={regionName}>
            <div className="region-banner">
              <span className="rname">{regionName}</span>
              <span className="region-tag">{regionCourses[0].region_theme}</span>
            </div>
            {regionCourses.map((course) => {
              const pct = Math.min(100, (course.xp_into_level / course.xp_to_next_level_snapshot) * 100)
              return (
                <div key={course.course_id} className="course-row">
                  <span className="course-name">{course.name}</span>
                  <div className="course-stats">
                    <span>
                      Mastery <b>Level {course.level}</b>
                    </span>
                    <span>
                      Difficulty <b>{course.difficulty_rating}</b>
                    </span>
                    <span>
                      Run <b>{course.times_run}×</b>
                    </span>
                  </div>
                  <div className="course-bar">
                    <div style={{ width: `${pct}%` }} />
                  </div>
                  <div className="course-map-slot">
                    <CourseMap polyline={course.polyline} theme={course.region_theme} courseName={course.name} />
                  </div>
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </section>
  )
}

export default CoursesPanel
