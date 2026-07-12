export const MULTIPLIER_LABELS: Record<string, string> = {
  elevation: 'Elevation',
  pr_bonus: 'Personal record',
  heat: 'Heat',
  course_difficulty: 'Course difficulty',
  goal_alignment: 'Goal alignment',
}

export function formatDistance(meters: number): string {
  return `${(meters / 1000).toFixed(1)} km`
}

export function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60)
  return `${minutes} min`
}

export function celsiusToFahrenheit(celsius: number): number {
  return Math.round((celsius * 9) / 5 + 32)
}
