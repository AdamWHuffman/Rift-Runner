"""Best-effort weather lookup for an activity's location/time, via Open-Meteo
(free, no API key). Same graceful-degradation pattern as region_engine's
geocode/theme lookups: any failure just means no weather bonus, never blocks
sync.
"""

from datetime import datetime, timezone

import httpx

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_TIMEOUT_SECONDS = 6.0
# Open-Meteo's standard forecast endpoint serves recent history via
# `past_days` (max 92) blended from its best available source for each day --
# simpler than the separate archive/reanalysis endpoint, which lags a few
# days behind real time and would miss "synced this morning" activities.
MAX_PAST_DAYS = 92


class WeatherResult:
    def __init__(self, temperature_c: float, humidity_pct: float, heat_index_c: float) -> None:
        self.temperature_c = temperature_c
        self.humidity_pct = humidity_pct
        self.heat_index_c = heat_index_c


def _heat_index_c(temp_c: float, humidity_pct: float) -> float:
    """NWS Rothfusz regression (defined in Fahrenheit). Heat index is only
    meaningfully different from air temperature above ~27C/80F -- below that
    NWS convention is that heat index equals the actual temperature."""
    temp_f = temp_c * 9 / 5 + 32
    if temp_f < 80:
        return temp_c

    rh = humidity_pct
    hi_f = (
        -42.379
        + 2.04901523 * temp_f
        + 10.14333127 * rh
        - 0.22475541 * temp_f * rh
        - 0.00683783 * temp_f * temp_f
        - 0.05481717 * rh * rh
        + 0.00122874 * temp_f * temp_f * rh
        + 0.00085282 * temp_f * rh * rh
        - 0.00000199 * temp_f * temp_f * rh * rh
    )
    return (hi_f - 32) * 5 / 9


def fetch_weather_at(lat: float, lon: float, when: datetime) -> WeatherResult | None:
    now = datetime.now(timezone.utc)
    when_utc = when.astimezone(timezone.utc) if when.tzinfo else when.replace(tzinfo=timezone.utc)
    days_ago = (now.date() - when_utc.date()).days
    if days_ago < 0 or days_ago > MAX_PAST_DAYS:
        return None

    try:
        response = httpx.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,relative_humidity_2m",
                "timezone": "UTC",
                "past_days": max(days_ago, 1),
                "forecast_days": 1,
            },
            timeout=WEATHER_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return None

    try:
        hourly = data["hourly"]
        target = when_utc.strftime("%Y-%m-%dT%H:00")
        index = hourly["time"].index(target)
        temp_c = float(hourly["temperature_2m"][index])
        humidity_pct = float(hourly["relative_humidity_2m"][index])
    except (KeyError, ValueError, IndexError, TypeError):
        return None

    return WeatherResult(
        temperature_c=temp_c,
        humidity_pct=humidity_pct,
        heat_index_c=_heat_index_c(temp_c, humidity_pct),
    )
