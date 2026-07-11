"""Maps a raw Garmin activity-list entry onto our Activity model's fields.

Garmin's list endpoint only gives us summary fields (no HR-zone breakdown or
GPS polyline) -- those get filled in by later phases as needed. The full raw
payload is always kept so nothing is lost if the mapping needs to improve.
"""

from datetime import datetime, timezone
from typing import Any


def map_activity(raw: dict[str, Any]) -> dict[str, Any]:
    activity_id = raw.get("activityId")
    start_time_gmt = raw.get("startTimeGMT")

    return {
        "garmin_activity_id": str(activity_id) if activity_id is not None else None,
        "activity_type": _activity_type(raw),
        "start_time": _parse_garmin_datetime(start_time_gmt) if start_time_gmt else datetime.now(timezone.utc),
        "duration_seconds": float(raw.get("duration") or 0),
        "distance_meters": float(raw.get("distance") or 0),
        "elevation_gain_meters": float(raw.get("elevationGain") or 0),
        "avg_hr": raw.get("averageHR"),
        "max_hr": raw.get("maxHR"),
        "calories": raw.get("calories"),
        "hr_seconds_in_zone": None,
        "polyline": None,
        "start_point": None,
        "end_point": None,
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
