from datetime import timezone

from app.services.garmin_sync.mapper import map_activity


def test_map_activity_extracts_summary_fields() -> None:
    raw = {
        "activityId": 123456789,
        "activityName": "Morning Run",
        "activityType": {"typeKey": "running"},
        "startTimeGMT": "2026-07-10 11:15:00",
        "duration": 1834.2,
        "distance": 5234.5,
        "elevationGain": 45.0,
        "elevationLoss": 42.0,
        "avgElevation": 12.5,
        "averageHR": 152.0,
        "maxHR": 178.0,
        "calories": 412.0,
        "steps": 6120,
        "averageSpeed": 2.85,
        "maxSpeed": 4.1,
        "averageRunningCadenceInStepsPerMinute": 168.0,
        "avgStrideLength": 106.4,
        "aerobicTrainingEffect": 3.4,
        "anaerobicTrainingEffect": 1.1,
        "vO2MaxValue": 47.0,
        "moderateIntensityMinutes": 20,
        "vigorousIntensityMinutes": 10,
        "pr": True,
        "hrTimeInZone_1": 200.0,
        "hrTimeInZone_2": 900.0,
        "hrTimeInZone_3": 600.0,
        "hrTimeInZone_4": 134.2,
        "hrTimeInZone_5": 0.0,
        "startLatitude": 38.88,
        "startLongitude": -77.1,
        "endLatitude": 38.89,
        "endLongitude": -77.09,
    }

    result = map_activity(raw)

    assert result["garmin_activity_id"] == "123456789"
    assert result["activity_name"] == "Morning Run"
    assert result["activity_type"] == "running"
    assert result["start_time"] == result["start_time"].replace(tzinfo=timezone.utc)
    assert result["start_time"].year == 2026
    assert result["duration_seconds"] == 1834.2
    assert result["distance_meters"] == 5234.5
    assert result["elevation_gain_meters"] == 45.0
    assert result["elevation_loss_meters"] == 42.0
    assert result["avg_elevation_meters"] == 12.5
    assert result["avg_hr"] == 152
    assert result["max_hr"] == 178
    assert result["calories"] == 412.0
    assert result["steps"] == 6120
    assert result["avg_speed_mps"] == 2.85
    assert result["max_speed_mps"] == 4.1
    assert result["avg_cadence_spm"] == 168.0
    assert result["avg_stride_length_cm"] == 106.4
    assert result["aerobic_training_effect"] == 3.4
    assert result["anaerobic_training_effect"] == 1.1
    assert result["vo2_max"] == 47.0
    assert result["moderate_intensity_minutes"] == 20
    assert result["vigorous_intensity_minutes"] == 10
    assert result["is_personal_record"] is True
    assert result["hr_seconds_in_zone"] == {"1": 200.0, "2": 900.0, "3": 600.0, "4": 134.2, "5": 0.0}
    assert result["start_point"] == {"lat": 38.88, "lon": -77.1}
    assert result["end_point"] == {"lat": 38.89, "lon": -77.09}
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
    assert result["steps"] is None
    assert result["vo2_max"] is None
    assert result["is_personal_record"] is None
    assert result["hr_seconds_in_zone"] is None
    assert result["start_point"] is None
    assert result["end_point"] is None


def test_map_activity_defaults_unknown_type_when_missing() -> None:
    result = map_activity({"activityId": 1})
    assert result["activity_type"] == "unknown"
