"""Best-effort weather lookup for an activity's location/time, via Open-Meteo
(free, no API key). Same graceful-degradation pattern as region_engine's
geocode/theme lookups: any failure just means no weather bonus, never blocks
sync.
"""

import math
from datetime import datetime, timedelta, timezone

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


def _apparent_temperature_c(temp_c: float, humidity_pct: float) -> float:
    """Australian Bureau of Meteorology's Apparent Temperature (wind term
    dropped -- we don't have reliable wind data at an activity's exact
    location/time): AT = Ta + 0.33*e - 4.0, where e is water vapor pressure
    derived from relative humidity.

    Chosen over the NWS heat index table specifically because it's
    continuous across the whole temperature range, rather than only being
    defined above ~27C/80F with humidity treated as irrelevant below that.
    A muggy 25C/87% day should (and now does) come out meaningfully warmer
    than a dry 25C day -- the old NWS-table approach couldn't express that
    at all below 80F, discarding humidity's contribution entirely in
    exactly the range most real runs happen in. Dry/cool conditions can
    legitimately come out *below* raw air temperature too (evaporative
    cooling), which is fine -- heat_multiplier() never lets that read as a
    penalty, just "further from the bonus threshold."
    """
    e = (humidity_pct / 100.0) * 6.105 * math.exp(17.27 * temp_c / (237.7 + temp_c))
    return temp_c + 0.33 * e - 4.0


def fetch_weather_at(lat: float, lon: float, when: datetime, duration_seconds: float = 0.0) -> WeatherResult | None:
    """Weighted average of every hourly sample the activity's actual
    [start, start+duration) window overlaps, weighted by how many seconds of
    each hour it spans -- not just a single point-sample at the start. A run
    that starts at 9:50 and continues into the 10:00 hour should mostly
    reflect the 10:00 reading, not the 9:00 one. duration_seconds<=0 (or
    omitted) falls back to sampling the single hour containing `when`."""
    now = datetime.now(timezone.utc)
    when_utc = when.astimezone(timezone.utc) if when.tzinfo else when.replace(tzinfo=timezone.utc)
    end_utc = when_utc + timedelta(seconds=duration_seconds if duration_seconds > 0 else 1.0)
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
        times = hourly["time"]
        temps = hourly["temperature_2m"]
        humidities = hourly["relative_humidity_2m"]
    except (KeyError, TypeError):
        return None

    weighted_temp = 0.0
    weighted_humidity = 0.0
    total_weight = 0.0
    for time_str, temp_c, humidity_pct in zip(times, temps, humidities):
        try:
            bucket_start = datetime.strptime(time_str, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        overlap_seconds = (min(end_utc, bucket_start + timedelta(hours=1)) - max(when_utc, bucket_start)).total_seconds()
        if overlap_seconds <= 0:
            continue
        weighted_temp += float(temp_c) * overlap_seconds
        weighted_humidity += float(humidity_pct) * overlap_seconds
        total_weight += overlap_seconds

    if total_weight <= 0:
        return None

    temp_c = weighted_temp / total_weight
    humidity_pct = weighted_humidity / total_weight

    return WeatherResult(
        temperature_c=temp_c,
        humidity_pct=humidity_pct,
        heat_index_c=_apparent_temperature_c(temp_c, humidity_pct),
    )
