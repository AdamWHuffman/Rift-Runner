// Route colors keyed by the region's real theme (region_engine/geocode.py
// THEME_* constants). Shared between CourseMap (single-route thumbnails) and
// WorldMap (the full multi-course map) so route colors read consistently
// across the app -- and so a future themed-biome reskin only has to touch
// one palette.
export const THEME_COLORS: Record<string, { line: string; start: string; end: string }> = {
  riverlands: { line: '#4a91a8', start: '#6fb3c9', end: '#4a91a8' },
  highlands: { line: '#7d4f8a', start: '#9b6fa8', end: '#7d4f8a' },
  greenwood: { line: '#416b40', start: '#5b8a5a', end: '#416b40' },
  metropolis: { line: '#d35f45', start: '#ef7f63', end: '#d35f45' },
}
export const DEFAULT_COLORS = THEME_COLORS.greenwood

export const TILE_URL = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
