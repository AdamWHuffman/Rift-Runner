export const MULTIPLIER_LABELS: Record<string, string> = {
  elevation: 'Elevation',
  pr_bonus: 'Personal record',
  heat: 'Heat',
  course_difficulty: 'Course difficulty',
  goal_alignment: 'Goal alignment',
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

// Accepts the raw UserResponse.units string rather than a narrower literal
// type -- anything other than exactly 'imperial' (including older/unset
// values) safely defaults to metric.
export function formatDistance(meters: number, units?: string): string {
  if (units === 'imperial') {
    return `${(meters / 1609.344).toFixed(1)} mi`
  }
  return `${(meters / 1000).toFixed(1)} km`
}

export function formatElevation(meters: number, units?: string): string {
  if (units === 'imperial') {
    return `${Math.round(meters * 3.28084)} ft`
  }
  return `${Math.round(meters)} m`
}

export function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60)
  return `${minutes} min`
}

export function celsiusToFahrenheit(celsius: number): number {
  return Math.round((celsius * 9) / 5 + 32)
}

export function xpProgressPct(user: { xp_into_level: number; xp_to_next_level_snapshot: number }): number {
  return Math.min(100, (user.xp_into_level / user.xp_to_next_level_snapshot) * 100)
}
