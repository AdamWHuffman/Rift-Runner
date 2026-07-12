export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

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

export interface SyncJobResponse {
  id: string
  status: 'queued' | 'running' | 'complete' | 'failed'
  activities_synced_count: number
  error_message: string | null
  started_at: string | null
  finished_at: string | null
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
