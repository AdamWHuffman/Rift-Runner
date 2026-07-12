import httpx
import pytest

from app.services.region_engine import geocode


class FakeResponse:
    def __init__(self, json_data, status_code: int = 200) -> None:
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._json_data


def test_geocode_address_returns_top_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **k: FakeResponse([{"lat": "38.88", "lon": "-77.09", "display_name": "Arlington, VA"}]),
    )

    result = geocode.geocode_address("Arlington, VA")

    assert result is not None
    assert result.lat == pytest.approx(38.88)
    assert result.lon == pytest.approx(-77.09)
    assert result.display_name == "Arlington, VA"


def test_geocode_address_returns_none_when_no_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse([]))
    assert geocode.geocode_address("Nowhere Land XYZ") is None


def test_geocode_address_returns_none_on_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_error(*a, **k):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(httpx, "get", raise_error)
    assert geocode.geocode_address("Arlington, VA") is None


def test_is_likely_united_states_true_for_arlington_va() -> None:
    assert geocode.is_likely_united_states(38.88, -77.09) is True


def test_is_likely_united_states_true_for_alaska_and_hawaii() -> None:
    assert geocode.is_likely_united_states(61.2, -149.9) is True  # Anchorage
    assert geocode.is_likely_united_states(21.3, -157.85) is True  # Honolulu


def test_is_likely_united_states_false_for_london() -> None:
    assert geocode.is_likely_united_states(51.5, -0.13) is False


def test_is_likely_united_states_false_for_mexico_city() -> None:
    assert geocode.is_likely_united_states(19.43, -99.13) is False


def test_detect_theme_prioritizes_water_over_hills(monkeypatch: pytest.MonkeyPatch) -> None:
    elements = [
        {"tags": {"natural": "peak"}},
        {"tags": {"waterway": "river"}},
    ]
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse({"elements": elements}))

    assert geocode.detect_theme(38.88, -77.09) == geocode.THEME_RIVERLANDS


def test_detect_theme_falls_back_to_highlands_without_water(monkeypatch: pytest.MonkeyPatch) -> None:
    elements = [{"tags": {"natural": "ridge"}}]
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse({"elements": elements}))

    assert geocode.detect_theme(38.88, -77.09) == geocode.THEME_HIGHLANDS


def test_detect_theme_falls_back_to_greenwood_for_parks_only(monkeypatch: pytest.MonkeyPatch) -> None:
    elements = [{"tags": {"leisure": "park"}}]
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse({"elements": elements}))

    assert geocode.detect_theme(38.88, -77.09) == geocode.THEME_GREENWOOD


def test_detect_theme_defaults_to_metropolis_when_nothing_distinctive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResponse({"elements": []}))
    assert geocode.detect_theme(38.88, -77.09) == geocode.THEME_METROPOLIS


def test_detect_theme_defaults_to_greenwood_on_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_error(*a, **k):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(httpx, "post", raise_error)
    assert geocode.detect_theme(38.88, -77.09) == geocode.DEFAULT_THEME
