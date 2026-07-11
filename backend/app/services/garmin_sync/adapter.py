"""Isolation boundary around the unofficial Garmin Connect library.

Everything in this app that needs to talk to Garmin goes through this module.
Garmin's unofficial API is a moving target (see docs/plan risk notes) — when it
breaks, this should be the only file that needs to change.

Confirmed against the installed `garminconnect` package source (not just docs):
- `Garmin(email, password, return_on_mfa=True)` + `.login()` returns
  `("needs_mfa", None)` when a code is required, `(None, None)` on success.
- `Garmin.resume_login(None, code)` completes a paused MFA login -- its first
  argument is accepted but unused by the library, so there's no separate
  "context" object to carry between requests; the same `Garmin` instance is
  the only thing that needs to be kept around between the two steps.
- Session state lives on `garmin.client` (a `garminconnect.client.Client`),
  serialized directly via `.dumps()` / `.loads(json_str)` -- a single JSON
  blob, not the two-file oauth1/oauth2 layout older garth-based code expects.
"""

import json
import time
import uuid
from datetime import date

from garminconnect import Garmin

MFA_SESSION_TTL_SECONDS = 300

# In-memory only: fine for a single-process local deployment. A multi-replica
# cloud deployment would need to move this to Redis (with the same TTL) since
# an in-progress MFA login must be resumed by the same process that started it.
_pending_mfa: dict[str, tuple[float, Garmin]] = {}


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
    client = Garmin(email=email, password=password, return_on_mfa=True)
    try:
        mfa_status, _legacy_token = client.login()
    except Exception as exc:
        raise GarminAuthError(str(exc)) from exc

    if mfa_status == "needs_mfa":
        _prune_expired_mfa_sessions()
        session_id = str(uuid.uuid4())
        _pending_mfa[session_id] = (time.time(), client)
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
    _, client = entry
    try:
        client.resume_login(None, code)
    except Exception as exc:
        raise GarminAuthError(str(exc)) from exc
    _pending_mfa.pop(mfa_session_id, None)
    return _dump_tokens(client)


def resume(tokens: dict[str, str]) -> Garmin:
    """Rebuild a logged-in Garmin client from previously saved tokens, without a password."""
    client = Garmin()
    try:
        client.client.loads(tokens["tokens"])
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
    return {"tokens": client.client.dumps()}


def _prune_expired_mfa_sessions() -> None:
    now = time.time()
    expired = [key for key, (started_at, _) in _pending_mfa.items() if now - started_at > MFA_SESSION_TTL_SECONDS]
    for key in expired:
        _pending_mfa.pop(key, None)
