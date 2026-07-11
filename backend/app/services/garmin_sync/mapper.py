"""Maps a raw Garmin activity-list entry onto our Activity model's fields.

Confirmed against a real synced activity: Garmin's list endpoint already
includes per-zone HR seconds (hrTimeInZone_1..5), start/end lat/lon, training
effect, VO2 max, cadence, speed, intensity minutes, steps and a PR flag
directly -- no extra detail call needed for any of this. The full GPS
polyline track does need a separate call (hasPolyline flag) -- deferred to
Phase 5 (course matching), which is the first thing that actually needs it.
The full raw payload is always kept so nothing is lost if the mapping needs
to improve.
"""

from datetime import datetime, timezone
from typing import Any


def map_activity(raw: dict[str, Any]) -> dict[str, Any]:
    activity_id = raw.get("activityId")
    start_time_gmt = raw.get("startTimeGMT")

    return {
        "garmin_activity_id": str(activity_id) if activity_id is not None else None,
        "activity_name": raw.get("activityName"),
        "activity_type": _activity_type(raw),
        "start_time": _parse_garmin_datetime(start_time_gmt) if start_time_gmt else datetime.now(timezone.utc),
        "duration_seconds": float(raw.get("duration") or 0),
        "distance_meters": float(raw.get("distance") or 0),
        "elevation_gain_meters": float(raw.get("elevationGain") or 0),
        "elevation_loss_meters": raw.get("elevationLoss"),
        "avg_elevation_meters": raw.get("avgElevation"),
        "avg_hr": _to_int(raw.get("averageHR")),
        "max_hr": _to_int(raw.get("maxHR")),
        "calories": raw.get("calories"),
        "steps": _to_int(raw.get("steps")),
        "avg_speed_mps": raw.get("averageSpeed"),
        "max_speed_mps": raw.get("maxSpeed"),
        "avg_cadence_spm": raw.get("averageRunningCadenceInStepsPerMinute"),
        "avg_stride_length_cm": raw.get("avgStrideLength"),
        "aerobic_training_effect": raw.get("aerobicTrainingEffect"),
        "anaerobic_training_effect": raw.get("anaerobicTrainingEffect"),
        "vo2_max": raw.get("vO2MaxValue"),
        "moderate_intensity_minutes": _to_int(raw.get("moderateIntensityMinutes")),
        "vigorous_intensity_minutes": _to_int(raw.get("vigorousIntensityMinutes")),
        "is_personal_record": raw.get("pr"),
        "hr_seconds_in_zone": _hr_seconds_in_zone(raw),
        "polyline": None,
        "start_point": _point(raw, "startLatitude", "startLongitude"),
        "end_point": _point(raw, "endLatitude", "endLongitude"),
        "raw_payload": raw,
        "processing_status": "pending",
    }


def _activity_type(raw: dict[str, Any]) -> str:
    activity_type = raw.get("activityType")
    if isinstance(activity_type, dict):
        return activity_type.get("typeKey", "unknown")
    return "unknown"


def _parse_garmin_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def _to_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def _hr_seconds_in_zone(raw: dict[str, Any]) -> dict[str, float] | None:
    zones = {}
    for zone in range(1, 6):
        value = raw.get(f"hrTimeInZone_{zone}")
        if value is not None:
            zones[str(zone)] = float(value)
    return zones or None


def _point(raw: dict[str, Any], lat_key: str, lon_key: str) -> dict[str, float] | None:
    lat = raw.get(lat_key)
    lon = raw.get(lon_key)
    if lat is None or lon is None:
        return None
    return {"lat": float(lat), "lon": float(lon)}
