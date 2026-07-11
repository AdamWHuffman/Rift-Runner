from datetime import timezone

from app.services.garmin_sync.mapper import map_activity


def test_map_activity_extracts_summary_fields() -> None:
    raw = {
        "activityId": 123456789,
        "activityType": {"typeKey": "running"},
        "startTimeGMT": "2026-07-10 11:15:00",
        "duration": 1834.2,
        "distance": 5234.5,
        "elevationGain": 45.0,
        "averageHR": 152,
        "maxHR": 178,
        "calories": 412.0,
    }

    result = map_activity(raw)

    assert result["garmin_activity_id"] == "123456789"
    assert result["activity_type"] == "running"
    assert result["start_time"] == result["start_time"].replace(tzinfo=timezone.utc)
    assert result["start_time"].year == 2026
    assert result["duration_seconds"] == 1834.2
    assert result["distance_meters"] == 5234.5
    assert result["elevation_gain_meters"] == 45.0
    assert result["avg_hr"] == 152
    assert result["max_hr"] == 178
    assert result["calories"] == 412.0
    assert result["raw_payload"] == raw
    assert result["processing_status"] == "pending"


def test_map_activity_handles_missing_optional_fields() -> None:
    raw = {"activityId": 1, "activityType": {"typeKey": "walking"}}

    result = map_activity(raw)

    assert result["duration_seconds"] == 0
    assert result["distance_meters"] == 0
    assert result["elevation_gain_meters"] == 0
    assert result["avg_hr"] is None
    assert result["calories"] is None


def test_map_activity_defaults_unknown_type_when_missing() -> None:
    result = map_activity({"activityId": 1})
    assert result["activity_type"] == "unknown"
