import { useEffect, useState } from 'react'
import { getCourses, type CourseProgressResponse } from '../api/client'

interface CoursesPanelProps {
  accessToken: string
  refreshKey: number
}

function CoursesPanel({ accessToken, refreshKey }: CoursesPanelProps) {
  const [courses, setCourses] = useState<CourseProgressResponse[] | null>(null)

  useEffect(() => {
    getCourses(accessToken)
      .then(setCourses)
      .catch(() => setCourses(null))
  }, [accessToken, refreshKey])

  if (!courses || courses.length === 0) return null

  return (
    <div className="courses-panel">
      <h2>Courses</h2>
      {courses.map((course) => (
        <div key={course.course_id} className="course-card">
          <strong>{course.name}</strong>
          <span className="course-region">
            {course.region_name} · {course.region_theme}
          </span>
          <p>
            Mastery Level {course.level} · Difficulty {course.difficulty_rating} · Run {course.times_run}x
          </p>
          <div className="xp-bar xp-bar-small">
            <div
              className="xp-bar-fill"
              style={{ width: `${Math.min(100, (course.xp_into_level / course.xp_to_next_level_snapshot) * 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

export default CoursesPanel
