// Defaults to whatever hostname the page itself was loaded from (just the
// backend's port swapped in), so the API origin always matches the page's
// origin -- whether that's localhost or a LAN IP. This matters beyond
// convenience: the refresh-token cookie is same-site only when the page and
// API share an origin, so hardcoding one fixed host here would silently
// break session persistence for anyone accessing via the other one.
// VITE_API_BASE_URL remains available as an explicit override if ever needed.
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:8000`

export interface AccessTokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface UserResponse {
  id: string
  email: string
  display_name: string
  units: string
  timezone: string
  main_level: number
  main_xp_total: number
  xp_into_level: number
  xp_to_next_level_snapshot: number
  activities_this_level: number
  onboarding_completed_at: string | null
}

export interface GarminStatusResponse {
  connected: boolean
  status: string | null
  last_sync_success_at: string | null
}

export interface GarminConnectResponse {
  connected: boolean
  status: string | null
  mfa_required: boolean
  mfa_session_id: string | null
}

export interface LevelUpEvent {
  type: 'main' | 'skill' | 'course'
  skill_key: string | null
  course_id: string | null
  course_name: string | null
  from_level: number
  to_level: number
}

export interface SyncJobResponse {
  id: string
  status: 'queued' | 'running' | 'complete' | 'failed'
  activities_synced_count: number
  error_message: string | null
  started_at: string | null
  finished_at: string | null
  level_up_events: LevelUpEvent[] | null
  new_activities: ActivitySummaryResponse[] | null
}

export interface SkillProgressResponse {
  key: string
  display_name: string
  level: number
  xp_into_level: number
  xp_to_next_level_snapshot: number
  activities_this_level: number
}

export interface RegionResponse {
  id: string
  name: string
  theme: string
}

export interface LatLon {
  lat: number
  lon: number
}

export interface CourseProgressResponse {
  course_id: string
  name: string
  activity_type: string
  region_name: string
  region_theme: string
  distance_meters: number
  elevation_gain_meters: number
  difficulty_rating: number
  level: number
  xp_into_level: number
  xp_to_next_level_snapshot: number
  times_run: number
  best_time_seconds: number | null
  polyline: LatLon[]
}

export interface GoalResponse {
  id: string
  key: string
  display_name: string
  description: string
  zone_weight_targets: number[]
}

export interface XPBreakdown {
  base_xp: number
  multipliers: Record<string, number>
  final_xp: number
  level_before: number
  level_after: number
}

export interface SkillXP {
  skill_key: string
  final_xp: number
}

export interface ActivitySummaryResponse {
  id: string
  activity_name: string | null
  activity_type: string
  start_time: string
  distance_meters: number
  duration_seconds: number
  elevation_gain_meters: number
  avg_hr: number | null
  is_personal_record: boolean | null
  course_name: string | null
  region_name: string | null
  temperature_c: number | null
  heat_index_c: number | null
  main_xp: XPBreakdown | null
  skill_xp: SkillXP[]
}

class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function parseErrorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json()
    return body.detail ?? res.statusText
  } catch {
    return res.statusText
  }
}

async function authedRequest<T>(
  path: string,
  accessToken: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      Authorization: `Bearer ${accessToken}`,
      ...init.headers,
    },
  })
  if (!res.ok) throw new ApiError(await parseErrorDetail(res), res.status)
  return res.json()
}

export async function login(email: string, password: string): Promise<AccessTokenResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) throw new ApiError(await parseErrorDetail(res), res.status)
  return res.json()
}

export async function getCurrentUser(accessToken: string): Promise<UserResponse> {
  return authedRequest<UserResponse>('/api/v1/auth/me', accessToken)
}

export async function completeOnboarding(accessToken: string): Promise<UserResponse> {
  return authedRequest<UserResponse>('/api/v1/auth/complete-onboarding', accessToken, { method: 'POST' })
}

export async function refreshAccessToken(): Promise<AccessTokenResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!res.ok) throw new ApiError(await parseErrorDetail(res), res.status)
  return res.json()
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  })
}

export async function connectGarmin(
  accessToken: string,
  email: string,
  password: string,
): Promise<GarminConnectResponse> {
  return authedRequest<GarminConnectResponse>('/api/v1/garmin/connect', accessToken, {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function completeGarminMfa(
  accessToken: string,
  mfaSessionId: string,
  code: string,
): Promise<GarminConnectResponse> {
  return authedRequest<GarminConnectResponse>('/api/v1/garmin/connect/mfa', accessToken, {
    method: 'POST',
    body: JSON.stringify({ mfa_session_id: mfaSessionId, code }),
  })
}

export async function getGarminStatus(accessToken: string): Promise<GarminStatusResponse> {
  return authedRequest<GarminStatusResponse>('/api/v1/garmin/status', accessToken)
}

export async function triggerSync(accessToken: string): Promise<SyncJobResponse> {
  return authedRequest<SyncJobResponse>('/api/v1/sync/trigger', accessToken, { method: 'POST' })
}

export async function getSyncJob(accessToken: string, jobId: string): Promise<SyncJobResponse> {
  return authedRequest<SyncJobResponse>(`/api/v1/sync/${jobId}`, accessToken)
}

export async function getSkills(accessToken: string): Promise<SkillProgressResponse[]> {
  return authedRequest<SkillProgressResponse[]>('/api/v1/skills', accessToken)
}

export async function setHomeBase(accessToken: string, address: string): Promise<RegionResponse> {
  return authedRequest<RegionResponse>('/api/v1/regions/home-base', accessToken, {
    method: 'POST',
    body: JSON.stringify({ address }),
  })
}

export async function getHomeBase(accessToken: string): Promise<RegionResponse | null> {
  return authedRequest<RegionResponse | null>('/api/v1/regions/home-base', accessToken)
}

export async function getCourses(accessToken: string): Promise<CourseProgressResponse[]> {
  return authedRequest<CourseProgressResponse[]>('/api/v1/courses', accessToken)
}

export async function getGoals(accessToken: string): Promise<GoalResponse[]> {
  return authedRequest<GoalResponse[]>('/api/v1/goals', accessToken)
}

export async function getActiveGoal(accessToken: string): Promise<GoalResponse | null> {
  return authedRequest<GoalResponse | null>('/api/v1/goals/active', accessToken)
}

export async function setActiveGoal(accessToken: string, goalKey: string): Promise<GoalResponse> {
  return authedRequest<GoalResponse>('/api/v1/goals/active', accessToken, {
    method: 'POST',
    body: JSON.stringify({ goal_key: goalKey }),
  })
}

export async function getActivities(accessToken: string, limit?: number): Promise<ActivitySummaryResponse[]> {
  const query = limit ? `?limit=${limit}` : ''
  return authedRequest<ActivitySummaryResponse[]>(`/api/v1/activities${query}`, accessToken)
}

export interface ImportableActivityResponse {
  garmin_activity_id: string
  activity_name: string | null
  activity_type: string
  start_time: string
  distance_meters: number
  duration_seconds: number
}

export async function deleteActivity(accessToken: string, activityId: string): Promise<UserResponse> {
  return authedRequest<UserResponse>(`/api/v1/activities/${activityId}`, accessToken, { method: 'DELETE' })
}

export async function getImportableActivities(accessToken: string): Promise<ImportableActivityResponse[]> {
  return authedRequest<ImportableActivityResponse[]>('/api/v1/activities/importable', accessToken)
}

export async function importActivities(accessToken: string, garminActivityIds: string[]): Promise<UserResponse> {
  return authedRequest<UserResponse>('/api/v1/activities/import', accessToken, {
    method: 'POST',
    body: JSON.stringify({ garmin_activity_ids: garminActivityIds }),
  })
}

export async function resetAccount(accessToken: string, confirm: string): Promise<UserResponse> {
  return authedRequest<UserResponse>('/api/v1/account/reset', accessToken, {
    method: 'POST',
    body: JSON.stringify({ confirm }),
  })
}
