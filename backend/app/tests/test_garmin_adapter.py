import pytest

from app.services.garmin_sync import adapter


class FakeClient:
    def __init__(self) -> None:
        self.loaded_tokens: str | None = None

    def dumps(self) -> str:
        return '{"di_token": "fake-token"}'

    def loads(self, tokenstore: str) -> None:
        if tokenstore == "invalid":
            raise Exception("bad tokens")
        self.loaded_tokens = tokenstore


class FakeGarmin:
    def __init__(self, mfa_flow: bool = False, activity_details: dict | None = None) -> None:
        self.client = FakeClient()
        self.mfa_flow = mfa_flow
        self.activity_details = activity_details or {}

    def login(self) -> tuple[str | None, None]:
        if self.mfa_flow:
            return "needs_mfa", None
        return None, None

    def resume_login(self, client_state: object, mfa_code: str) -> tuple[None, None]:
        if mfa_code != "123456":
            raise Exception("invalid MFA code")
        return None, None

    def get_activity_details(self, activity_id: str) -> dict:
        return self.activity_details


def _fake_garmin_factory(mfa_flow: bool):
    def factory(
        email: str | None = None,
        password: str | None = None,
        return_on_mfa: bool = False,
    ) -> FakeGarmin:
        return FakeGarmin(mfa_flow=mfa_flow)

    return factory


def test_connect_returns_tokens_without_mfa(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "Garmin", _fake_garmin_factory(mfa_flow=False))

    tokens = adapter.connect("someone@example.com", "password")

    assert tokens["tokens"] == '{"di_token": "fake-token"}'


def test_connect_raises_mfa_required_and_tracks_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "Garmin", _fake_garmin_factory(mfa_flow=True))

    with pytest.raises(adapter.GarminMfaRequiredError) as exc_info:
        adapter.connect("someone@example.com", "password")

    assert exc_info.value.mfa_session_id in adapter._pending_mfa


def test_complete_mfa_with_correct_code_returns_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "Garmin", _fake_garmin_factory(mfa_flow=True))
    with pytest.raises(adapter.GarminMfaRequiredError) as exc_info:
        adapter.connect("someone@example.com", "password")
    session_id = exc_info.value.mfa_session_id

    tokens = adapter.complete_mfa(session_id, "123456")

    assert tokens["tokens"] == '{"di_token": "fake-token"}'
    assert session_id not in adapter._pending_mfa


def test_complete_mfa_with_wrong_code_raises_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "Garmin", _fake_garmin_factory(mfa_flow=True))
    with pytest.raises(adapter.GarminMfaRequiredError) as exc_info:
        adapter.connect("someone@example.com", "password")
    session_id = exc_info.value.mfa_session_id

    with pytest.raises(adapter.GarminAuthError):
        adapter.complete_mfa(session_id, "000000")

    assert session_id in adapter._pending_mfa, "a wrong code should not consume the pending session"


def test_complete_mfa_with_unknown_session_raises_auth_error() -> None:
    with pytest.raises(adapter.GarminAuthError):
        adapter.complete_mfa("does-not-exist", "123456")


def test_resume_loads_tokens_into_fresh_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "Garmin", _fake_garmin_factory(mfa_flow=False))

    client = adapter.resume({"tokens": "some-token-blob"})

    assert client.client.loaded_tokens == "some-token-blob"


def test_resume_raises_auth_error_on_bad_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "Garmin", _fake_garmin_factory(mfa_flow=False))

    with pytest.raises(adapter.GarminAuthError):
        adapter.resume({"tokens": "invalid"})


def test_serialize_deserialize_tokens_roundtrip() -> None:
    tokens = {"tokens": '{"di_token": "abc"}'}
    assert adapter.deserialize_tokens(adapter.serialize_tokens(tokens)) == tokens


def test_fetch_activity_polyline_extracts_lat_lon() -> None:
    client = FakeGarmin(
        activity_details={
            "geoPolylineDTO": {
                "polyline": [
                    {"lat": 38.86, "lon": -77.05, "altitude": None, "time": 123},
                    {"lat": 38.87, "lon": -77.04, "altitude": None, "time": 456},
                ]
            }
        }
    )

    points = adapter.fetch_activity_polyline(client, "12345")

    assert points == [{"lat": 38.86, "lon": -77.05}, {"lat": 38.87, "lon": -77.04}]


def test_fetch_activity_polyline_returns_none_when_missing() -> None:
    client = FakeGarmin(activity_details={"geoPolylineDTO": {}})
    assert adapter.fetch_activity_polyline(client, "12345") is None


def test_fetch_activity_polyline_returns_none_on_error() -> None:
    class BrokenClient:
        def get_activity_details(self, activity_id: str) -> dict:
            raise Exception("network error")

    assert adapter.fetch_activity_polyline(BrokenClient(), "12345") is None
