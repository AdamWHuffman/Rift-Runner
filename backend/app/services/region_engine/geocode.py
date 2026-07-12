"""Address -> coordinates, and coordinates -> a region theme.

Both calls are best-effort against free OSM services (Nominatim, Overpass):
short timeouts, broad exception handling, graceful fallback to a generic
theme. Geocoding failure returns None (the caller decides what that means);
theme detection never fails outward at all -- worst case it's just generic.
"""

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "QuestForHealth/0.1 (personal fitness app)"

GEOCODE_TIMEOUT_SECONDS = 8.0
OVERPASS_TIMEOUT_SECONDS = 6.0
FEATURE_SEARCH_RADIUS_METERS = 3000

THEME_RIVERLANDS = "riverlands"
THEME_HIGHLANDS = "highlands"
THEME_METROPOLIS = "metropolis"
THEME_GREENWOOD = "greenwood"
DEFAULT_THEME = THEME_GREENWOOD


class GeocodeResult:
    def __init__(self, lat: float, lon: float, display_name: str) -> None:
        self.lat = lat
        self.lon = lon
        self.display_name = display_name


def geocode_address(address: str) -> GeocodeResult | None:
    try:
        response = httpx.get(
            NOMINATIM_URL,
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=GEOCODE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        results = response.json()
    except Exception:
        return None

    if not results:
        return None
    top = results[0]
    try:
        return GeocodeResult(lat=float(top["lat"]), lon=float(top["lon"]), display_name=top.get("display_name", address))
    except (KeyError, ValueError, TypeError):
        return None


_OVERPASS_QUERY = """
[out:json][timeout:5];
(
  way["waterway"="river"](around:{radius},{lat},{lon});
  way["natural"="water"](around:{radius},{lat},{lon});
  node["natural"="peak"](around:{radius},{lat},{lon});
  way["natural"="ridge"](around:{radius},{lat},{lon});
  way["leisure"="park"](around:{radius},{lat},{lon});
  way["natural"="wood"](around:{radius},{lat},{lon});
);
out tags 20;
"""


def is_likely_united_states(lat: float, lon: float) -> bool:
    """Rough bounding-box check (continental US, Alaska, Hawaii, Puerto
    Rico) -- good enough to pick a sensible units default (imperial vs
    metric) without an extra geocoding round-trip on every home-base save.
    Known imprecision: southern Canada shares the same lat/lon band as the
    northern US, so a home base there would misclassify as US. That's a
    wrong-but-still-reasonable unit default, not worth a network call and
    its own failure mode to avoid."""
    conus = 24.5 <= lat <= 49.5 and -125.0 <= lon <= -66.9
    alaska = 51.0 <= lat <= 71.5 and -179.5 <= lon <= -129.0
    hawaii = 18.5 <= lat <= 22.5 and -160.5 <= lon <= -154.5
    puerto_rico = 17.8 <= lat <= 18.6 and -67.5 <= lon <= -65.2
    return conus or alaska or hawaii or puerto_rico


def detect_theme(lat: float, lon: float) -> str:
    """Priority: riverlands > highlands > greenwood > metropolis (fallback
    when nothing distinctive is nearby, or the lookup fails/times out)."""
    try:
        response = httpx.post(
            OVERPASS_URL,
            data={"data": _OVERPASS_QUERY.format(radius=FEATURE_SEARCH_RADIUS_METERS, lat=lat, lon=lon)},
            headers={"User-Agent": USER_AGENT},
            timeout=OVERPASS_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        elements = response.json().get("elements", [])
    except Exception:
        return DEFAULT_THEME

    has_water = False
    has_high_ground = False
    has_greenery = False

    for element in elements:
        tags = element.get("tags", {})
        if tags.get("waterway") == "river" or tags.get("natural") == "water":
            has_water = True
        elif tags.get("natural") in ("peak", "ridge"):
            has_high_ground = True
        elif tags.get("leisure") == "park" or tags.get("natural") == "wood":
            has_greenery = True

    if has_water:
        return THEME_RIVERLANDS
    if has_high_ground:
        return THEME_HIGHLANDS
    if has_greenery:
        return THEME_GREENWOOD
    return THEME_METROPOLIS
