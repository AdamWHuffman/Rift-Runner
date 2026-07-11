from pathlib import Path

import pytest

from app.services.garmin_sync import adapter


class FakeGarth:
    def __init__(self, mfa_flow: bool) -> None:
        self.mfa_flow = mfa_flow

    def login(self, email: str, password: str, return_on_mfa: bool = False) -> tuple[str, object]:
        if self.mfa_flow:
            return "needs_mfa", {"context": "fake"}
        return "success", None

    def resume_login(self, mfa_context: object, code: str) -> None:
        if code != "123456":
            raise Exception("invalid MFA code")

    def dump(self, directory: str) -> None:
        Path(directory, "oauth1_token.json").write_text('{"token": "oauth1"}')
        Path(directory, "oauth2_token.json").write_text('{"token": "oauth2"}')


class FakeGarmin:
    def __init__(self, mfa_flow: bool = False) -> None:
        self.garth = FakeGarth(mfa_flow=mfa_flow)


def _fake_garmin_factory(mfa_flow: bool):
    def factory(email: str | None = None, password: str | None = None) -> FakeGarmin:
        return FakeGarmin(mfa_flow=mfa_flow)

    return factory


def test_connect_returns_tokens_without_mfa(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "Garmin", _fake_garmin_factory(mfa_flow=False))

    tokens = adapter.connect("someone@example.com", "password")

    assert tokens["oauth1_token.json"] == '{"token": "oauth1"}'
    assert tokens["oauth2_token.json"] == '{"token": "oauth2"}'


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

    assert tokens["oauth1_token.json"] == '{"token": "oauth1"}'
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


def test_serialize_deserialize_tokens_roundtrip() -> None:
    tokens = {"oauth1_token.json": "a", "oauth2_token.json": "b"}
    assert adapter.deserialize_tokens(adapter.serialize_tokens(tokens)) == tokens
