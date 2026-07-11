"""Isolation boundary around the unofficial Garmin Connect library.

Everything in this app that needs to talk to Garmin goes through this module.
Garmin's unofficial API is a moving target (see docs/plan risk notes) — when it
breaks, this should be the only file that needs to change.

MFA note: garth's `login(..., return_on_mfa=True)` / `resume_login(...)` pair is
the documented way to support MFA in a non-interactive (server) context, but it
hasn't been exercised against a real MFA-enabled account yet -- if Garmin's
actual response shape differs, this is the piece most likely to need a tweak.
"""

import json
import tempfile
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from garminconnect import Garmin

TOKEN_FILENAMES = ("oauth1_token.json", "oauth2_token.json")
MFA_SESSION_TTL_SECONDS = 300

# In-memory only: fine for a single-process local deployment. A multi-replica
# cloud deployment would need to move this to Redis (with the same TTL) since
# an in-progress MFA login must be resumed by the same process that started it.
_pending_mfa: dict[str, tuple[float, Garmin, Any]] = {}


class GarminAuthError(Exception):
    """Raised when Garmin credentials or a saved session are invalid/expired."""


class GarminSyncError(Exception):
    """Raised for any other failure talking to Garmin (network, rate limit, etc.)."""


class GarminMfaRequiredError(Exception):
    """Raised mid-login when Garmin requires an MFA code to proceed."""

    def __init__(self, mfa_session_id: str) -> None:
        self.mfa_session_id = mfa_session_id
        super().__init__("MFA code required to complete Garmin login")


def connect(email: str, password: str) -> dict[str, str]:
    """Perform a fresh Garmin login and return the resulting session tokens.

    Raises GarminMfaRequiredError if Garmin asks for an MFA code -- call
    complete_mfa() with the returned session id once the user supplies it.
    """
    client = Garmin(email=email, password=password)
    try:
        result1, result2 = client.garth.login(email, password, return_on_mfa=True)
    except Exception as exc:
        raise GarminAuthError(str(exc)) from exc

    if result1 == "needs_mfa":
        _prune_expired_mfa_sessions()
        session_id = str(uuid.uuid4())
        _pending_mfa[session_id] = (time.time(), client, result2)
        raise GarminMfaRequiredError(session_id)

    return _dump_tokens(client)


def complete_mfa(mfa_session_id: str, code: str) -> dict[str, str]:
    """Finish a login that paused for MFA, using the code the user provided.

    A wrong code leaves the session in place so the user can retry without
    re-entering their password -- only a successful login consumes it.
    """
    entry = _pending_mfa.get(mfa_session_id)
    if entry is None:
        raise GarminAuthError("MFA session expired or not found, please reconnect")
    _, client, mfa_context = entry
    try:
        client.garth.resume_login(mfa_context, code)
    except Exception as exc:
        raise GarminAuthError(str(exc)) from exc
    _pending_mfa.pop(mfa_session_id, None)
    return _dump_tokens(client)


def resume(tokens: dict[str, str]) -> Garmin:
    """Rebuild a logged-in Garmin client from previously saved tokens, without a password."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for filename, contents in tokens.items():
            (tmp_path / filename).write_text(contents)
        try:
            client = Garmin()
            client.login(tmp_path.as_posix())
        except Exception as exc:
            raise GarminAuthError(str(exc)) from exc
    return client


def fetch_activities_since(client: Garmin, since: date) -> list[dict]:
    try:
        return client.get_activities_by_date(since.isoformat(), date.today().isoformat())
    except Exception as exc:
        raise GarminSyncError(str(exc)) from exc


def serialize_tokens(tokens: dict[str, str]) -> str:
    return json.dumps(tokens)


def deserialize_tokens(blob: str) -> dict[str, str]:
    return json.loads(blob)


def _dump_tokens(client: Garmin) -> dict[str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        client.garth.dump(tmp)
        return {name: (tmp_path / name).read_text() for name in TOKEN_FILENAMES if (tmp_path / name).exists()}


def _prune_expired_mfa_sessions() -> None:
    now = time.time()
    expired = [key for key, (started_at, _, _) in _pending_mfa.items() if now - started_at > MFA_SESSION_TTL_SECONDS]
    for key in expired:
        _pending_mfa.pop(key, None)
