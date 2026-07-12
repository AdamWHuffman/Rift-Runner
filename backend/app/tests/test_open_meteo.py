from datetime import datetime, timezone

import httpx
import pytest

from app.services.weather import open_meteo


class FakeResponse:
    def __init__(self, json_data, status_code: int = 200) -> None:
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json_data


def _hourly_payload(hour_iso: str, temp_c: float, humidity_pct: float):
    return {
        "hourly": {
            "time": ["2026-07-11T00:00", hour_iso, "2026-07-11T02:00"],
            "temperature_2m": [18.0, temp_c, 19.0],
            "relative_humidity_2m": [60.0, humidity_pct, 55.0],
        }
    }


def test_fetch_weather_at_returns_temp_and_humidity_for_matching_hour(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse(_hourly_payload("2026-07-11T01:00", 30.0, 70.0))
    )

    result = open_meteo.fetch_weather_at(38.86, -77.05, datetime(2026, 7, 11, 1, 30, tzinfo=timezone.utc))

    assert result is not None
    assert result.temperature_c == pytest.approx(30.0)
    assert result.humidity_pct == pytest.approx(70.0)


def test_fetch_weather_at_computes_heat_index_for_hot_humid_conditions(monkeypatch: pytest.MonkeyPatch) -> None:
    # 35C / 70% humidity is a real "danger"-range combination -- heat index
    # should come out noticeably higher than the raw air temperature.
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse(_hourly_payload("2026-07-11T01:00", 35.0, 70.0))
    )

    result = open_meteo.fetch_weather_at(38.86, -77.05, datetime(2026, 7, 11, 1, 0, tzinfo=timezone.utc))

    assert result is not None
    assert result.heat_index_c > result.temperature_c + 5


def test_fetch_weather_at_heat_index_equals_temp_below_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse(_hourly_payload("2026-07-11T01:00", 15.0, 50.0))
    )

    result = open_meteo.fetch_weather_at(38.86, -77.05, datetime(2026, 7, 11, 1, 0, tzinfo=timezone.utc))

    assert result is not None
    assert result.heat_index_c == pytest.approx(result.temperature_c)


def test_fetch_weather_at_returns_none_on_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_error(*a, **k):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(httpx, "get", raise_error)
    result = open_meteo.fetch_weather_at(38.86, -77.05, datetime.now(timezone.utc))
    assert result is None


def test_fetch_weather_at_returns_none_when_hour_not_in_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: FakeResponse(_hourly_payload("2026-07-11T01:00", 30.0, 70.0))
    )
    # Asking for an hour far outside the tiny fake payload's time range.
    result = open_meteo.fetch_weather_at(38.86, -77.05, datetime(2026, 7, 11, 23, 0, tzinfo=timezone.utc))
    assert result is None


def test_fetch_weather_at_returns_none_for_future_dates() -> None:
    far_future = datetime(2099, 1, 1, tzinfo=timezone.utc)
    assert open_meteo.fetch_weather_at(38.86, -77.05, far_future) is None
