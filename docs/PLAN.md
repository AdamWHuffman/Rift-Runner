# The Quest for Health — Plan & Progress

This file combines the original approved build plan with a running log of what's
actually been built and verified, so either can be referenced later without
digging through chat history. The original plan is preserved as-approved below;
the Progress Log after it reflects reality as of the last update.

---

## Original Plan (as approved)

### Context

You want a gamified fitness web app that pulls in your Garmin activity data and turns every run/walk into an RPG-style progression loop: a main character level, independent skill stats, and a personalized "course" leveling system for the specific routes you run — all wrapped in a fun, "rogue RuneScape"-style presentation with real animation and sound so leveling up actually feels good. The two systems you called out as top priority are (1) the main leveling algorithm's pacing/dopamine feel, and (2) the course-leveling algorithm, which must be personalized per user rather than a fixed difficulty rating. You also want a "Home Base" region (based on Arlington, VA, but never literally named that) with fun generated names, a goals system that changes what the algorithm rewards (e.g. general health shouldn't reward redlining your heart rate), and an architecture that stays easy to extend as you add features later.

This is a from-scratch build. Confirmed direction: **Python/FastAPI backend + React/TypeScript frontend**, Garmin data via the **unofficial `garminconnect`/`garth` libraries** (no official Health API approval), **single-user today but built multi-user-ready** (real auth/user model from day one, just one account), and **local development now with a cloud-portable architecture** (Postgres, containerized) in case this grows later.

### Key Decisions & Assumptions

| Area | Decision | Rationale |
|---|---|---|
| Auth | Hand-rolled JWT (access+refresh) via `PyJWT` + `pwdlib[argon2]` for hashing — not `fastapi-users`, not `passlib` | `User` model is domain-heavy from day 1; a small custom auth module avoids fighting a framework. `passlib` is unmaintained. Multi-user-readiness is structural (every table is `user_id`-keyed; public signup exists but is feature-flag gated off for now) |
| DB / ORM | PostgreSQL 16 + SQLAlchemy 2.0 (async) + Alembic | Portable to any cloud Postgres later with zero migration-story rewrite |
| Garmin library | `python-garminconnect` (wraps garth-style auth, includes TLS-impersonation login to survive Garmin's bot defenses) | See risk callout below |
| Background jobs | Redis + `arq` from day one | Matches "cloud-portable," pairs naturally with FastAPI's async style |
| Sync status delivery | Simple polling (`GET /sync/{id}` every ~1.2s), not SSE/WebSocket | Only one small job runs at a time for one user; simple and plenty snappy |
| Frontend state | Zustand (client) + TanStack Query (server/polling) — not yet introduced, still plain React state as of Phase 3 | Standard pairing for this kind of dashboard+polling app; will be adopted when data-fetching complexity actually needs it |

### ⚠️ Biggest Risk: Garmin's Unofficial API Is Volatile

Garmin has been actively hardening its login flow against bot/automation traffic. Old `garth`-based assumptions can go stale; the actual installed library's API had to be read directly from source rather than trusted from memory (see Progress Log — this happened for real during Phase 2).

Mitigations built in: (1) **Isolation boundary** — all Garmin SDK usage lives behind `garmin_sync/adapter.py`; when Garmin breaks something, only this file changes. (2) **Manual import fallback** (Phase 2.5, not yet built) — upload a `.fit`/`.gpx` export as a second ingestion path into the same `activities` table, so the app still works during a Garmin auth outage.

### Architecture Overview

**Monorepo**: `backend/` (FastAPI) + `frontend/` (React/Vite/TS) + `docker-compose.yml` (postgres, redis, backend api, backend worker, frontend).

**Backend service modules** (`backend/app/services/`):
- `garmin_sync/` — `adapter.py` (isolated 3rd-party wrapper), `mapper.py` (Garmin payload → Activity row), `sync_service.py` (orchestrates one sync run)
- `xp_engine/` — `leveling.py` (the shared adaptive leveling curve, reused by main/skill/course leveling), `formulas.py` (TRIMP + multipliers), `calculator.py` (orchestrates one activity → all XP transactions)
- `course_engine/` — not yet built (Phase 5)
- `region_engine/` — not yet built (Phase 5)
- `goal_engine/` — not yet built (Phase 6)
- `weather/` — not yet built (Phase 8)

**One activity's lifecycle**: Garmin sync inserts a raw `activities` row → (Phase 5: `course_engine` matches it to an existing course or creates a new one) → `xp_engine.calculator` computes base XP (TRIMP) → applies multipliers (elevation, PR bonus; course-difficulty and goal-alignment currently stubbed at 1.0) → writes an immutable `xp_transactions` row → `leveling.py` updates denormalized levels and returns any level-up events → recorded on the sync job for the frontend to eventually animate (Phase 7).

### Garmin Integration & Sync Flow

Tokens are stored **encrypted at rest** (Fernet, key from env var) in `garmin_credentials`. Raw password is used once and never stored. Sync-on-every-open: `POST /api/v1/sync/trigger` debounces (won't re-hit Garmin if a sync succeeded in the last 2 minutes or one's already running — but a *failed* job does NOT debounce, so retry is always immediate), enqueues an `arq` background job, returns immediately. Dashboard renders from cached DB data; frontend polls job status.

### Data Model (core tables, as originally sketched)

`users`, `garmin_credentials`, `sync_jobs`, `activities`, `courses`, `course_activity_links`, `course_user_progress`, `regions`, `goals`, `user_goal_history`, `skills`, `skill_progress`, `xp_transactions` (append-only immutable audit log), `achievements`/`user_achievements`, `rule_configs`.

*(Actual schema built so far is narrower than this full sketch — only what each completed phase needs. See Progress Log.)*

### Core Algorithm: Main Leveling (the dopamine engine) — ✅ built, see Progress Log

Decouples **activities-per-level** (`activities_to_next_level(L) = min(10, 5 + L // 6)` — a pure function of level, hard-bounded to [5,10]) from **XP-per-level** (anchored to a rolling EMA of the user's own XP-per-activity, frozen as a snapshot target the moment each level starts). A hard guarantee forces a level-up on the Nth activity even if the XP target technically hasn't been hit yet.

### Core Algorithm: XP Formula — ✅ built, see Progress Log

```
trimp = Σ(minutes_in_zone[z] * z)   for z in 1..5
base_xp = trimp * 10
```
(fallback: `calories * 0.5 + duration_minutes * 1.5` when no HR data). Multiplicative bonuses: elevation (+up to 50%), heat index (not yet wired, Phase 8), course-difficulty (stubbed 1.0, Phase 5), PR bonus (+50% flat, currently sourced from Garmin's own PR flag), goal alignment (stubbed 1.0, Phase 6).

### Core Algorithm: Skill System — ✅ built (Speed/Endurance/Health/Consistency), see Progress Log

Explorer deferred to Phase 5 (needs course/region discovery to exist first).

### Core Algorithm: Course Leveling — not yet built (Phase 5)

Planned: geohash-bucketed route matching, personalized `difficulty_rating_at_discovery` (scaled by the user's own Endurance skill), separate ever-increasing mastery `level`, repeat-run XP decay floored at 30%.

### Home Base & Region Naming — not yet built (Phase 5)

Planned: onboarding explicitly prompts for a home address (not inferred from activity data) → geocode → theme from dominant geographic feature → deterministically-seeded fantasy name generator. Example names generated for Arlington, VA during planning: *The Ridgeway Spires*, *Potomac's Landing*, *Glasshaven Heights*, *The Fourmile Reaches*, *Ridgemont Crossing*.

### Goals System — not yet built (Phase 6)

Planned: `general_health` / `endurance_building` / `performance_racing`, each a target HR-zone-time distribution driving a 0.7×–1.3× goal-alignment multiplier.

### Frontend UX — "Rogue RuneScape" Feel — not yet built (Phase 7)

Planned: Framer Motion, canvas-confetti, Howler.js + Kenney.nl CC0 assets, parchment/pixel-art visual language. Current frontend is deliberately bare-bones (Phase 0-3 just needed enough UI to prove each backend piece works).

### Extensibility Mechanism

Two-tier: Tier 1 declarative rules (`rule_configs` table, not yet built) for simple multipliers; Tier 2 registered functions (already the pattern used for skills-to-come) for logic needing real state. Every `xp_transactions` row is versioned (`formula_version`) and stores fully-resolved multipliers, so history stays explainable even as formulas evolve; `raw_payload` on every activity retains the full original Garmin response so nothing is ever lost even before a field is promoted to a real column.

### Phased Build Roadmap

0. Scaffolding — ✅ complete
1. Auth & Users — ✅ complete
2. Garmin ingestion — ✅ complete
2.5. Manual import fallback — ⬜ not started
3. Core XP & main leveling — ✅ complete
4. Skills — ✅ complete (Speed/Endurance/Health/Consistency; Explorer deferred to Phase 5)
5. Courses & Regions — ⬜ not started (next up)
6. Goals — ⬜ not started
7. Gamified frontend polish — ⬜ not started
8. Auto-sync-on-load + weather — ⬜ not started (basic sync-trigger exists; the full "always sync on open" polish is pending)
9. Cloud-deploy prep — ⬜ not started

### Verification Plan (as originally written)

- Phase 0-2: `docker compose up`, health check, real Garmin connect+sync
- Phase 3-4: unit tests on the leveling guarantee, TRIMP/multiplier calculator tests, xp_transactions correctness
- Phase 5-6: route-matching dedup test, region naming, goal-switching multiplier test
- Phase 7-8: live browser walkthrough of the full sync → celebration → dashboard loop

---

## Progress Log

### Phase 0 — Scaffolding ✅ complete & verified
FastAPI + Vite/React/TS monorepo, Docker Compose (postgres/redis/backend/worker/frontend), Alembic initialized. Dev environment runs via WSL Ubuntu (user's preference over native PowerShell). Node installed via nvm; a real npm optional-dependencies bug (Windows-resolved native bindings in the lockfile) was hit and fixed by reinstalling with the Linux npm. Git repo initialized locally.

### Phase 1 — Auth & Users ✅ complete & verified
`User` model, JWT access+refresh (httpOnly cookie for refresh), password hashing via pwdlib/argon2, register (signup-gated off)/login/refresh/logout/me endpoints, `create_user.py` bootstrap script. Verified end-to-end against real Postgres via Docker Compose (wrong password → 401, correct login → tokens, `/me` works, refresh works, registration correctly blocked).

### Phase 2 — Garmin Ingestion ✅ complete & verified (including real account + MFA)
Built `garmin_sync/adapter.py`, `mapper.py`, `sync_service.py`; `garmin_credentials`/`sync_jobs`/`activities` tables; debounced `/sync/trigger` + `/sync/{id}` polling; arq worker wired to a real `run_garmin_sync` job.

**Real bugs found and fixed during live testing (not caught by unit tests, since they were about the *actual* third-party library's API shape):**
- Initial adapter was built against assumed `garth`-style API (`Garmin.garth`, two-file oauth1/oauth2 tokens, `login(email, password, return_on_mfa=...)`). Real error: `'Garmin' object has no attribute 'garth'`. Fixed by reading the actually-installed `garminconnect` package source directly — the real API uses `Garmin.client` (not `.garth`), a single JSON token blob via `.dumps()`/`.loads()`, and `return_on_mfa` is a **constructor** kwarg, not a `login()` kwarg. `resume_login(client_state, code)` ignores `client_state` entirely — the same `Garmin` instance just needs to be kept around in memory between the two MFA steps.
- MFA support wasn't in the original plan's Phase 2 scope but was added once discovered the user's real account requires it: two-step `/garmin/connect` → (if `mfa_required`) → `/garmin/connect/mfa`.
- Fixed a real bug where a wrong MFA code would have deleted the pending session (forcing a full password re-entry) instead of allowing retry.
- The mapper initially assumed HR-zone-seconds and GPS start/end points needed a separate Garmin API detail call — confirmed against a real synced activity that they're already present in the basic activity-list response (`hrTimeInZone_1..5`, `startLatitude`/`startLongitude` etc.), no extra call needed.

Per user direction ("factor in pretty much every stat you can pull from the Garmin API"), the `Activity` table was deliberately widened beyond the original plan's sketch: `activity_name`, `steps`, `avg_speed_mps`/`max_speed_mps`, `avg_cadence_spm`, `avg_stride_length_cm`, `aerobic_training_effect`/`anaerobic_training_effect`, `vo2_max`, `moderate_intensity_minutes`/`vigorous_intensity_minutes`, `is_personal_record` (Garmin's own PR flag), `elevation_loss_meters`/`avg_elevation_meters`, plus `hr_seconds_in_zone`/`start_point`/`end_point`. Full raw Garmin payload always retained in `raw_payload` regardless, so nothing is ever lost even before a field is promoted to a real column.

### Phase 3 — Core XP Engine & Main Leveling ✅ complete & verified
`xp_engine/leveling.py` (the shared adaptive leveling primitive), `formulas.py` (TRIMP + elevation + PR-bonus multipliers, course-difficulty/goal-alignment stubbed at 1.0), `calculator.py` (orchestration + `xp_transactions`). Wired into `sync_service` so every new activity earns real XP; `sync_jobs.level_up_events` records what fired.

209 dedicated leveling tests including a randomized simulation proving the 5-10-activities-per-level guarantee holds structurally (only the *upper* bound of 10 is a hard invariant — a strong performance streak can legitimately clear a level in fewer than 5 activities, which is a feature, not a bug). 245 backend tests total, all passing.

**Real-world result**: re-synced the connected real account's activity through the full pipeline — first activity earned 1447 XP (TRIMP from real HR-zone data × elevation bonus) and triggered an immediate level 1 → 2 level-up, matching hand calculations exactly.

Frontend: added a basic (intentionally unstyled — Phase 7 will make it pretty) level/XP display to `App.tsx`, with a refresh callback wired from `GarminPanel` so it updates after a sync completes.

### Phase 4 — Skills ✅ complete & verified
`skill_formulas.py` (pure, ratio-based XP for Speed/Endurance/Health/Consistency — each compares the current activity to the user's own recent baseline, with a floor so an off day still earns something and a cap so no outlier trivializes the skill), `skills.py` (Tier-2 registered-function orchestration, `SKILL_CALCULATORS` dict, reuses `xp_engine.leveling` verbatim with each skill's own independent `SkillProgress`/EMA). Speed/Endurance/Health compare within the same activity type; Consistency spans all types. `skills`/`skill_progress` tables, `config_data/skills.yaml` + `seed_config.py` for the catalog, `GET /api/v1/skills` exposes progress (defaulting missing skills to a sensible level-1 entry). Wired into `sync_service` alongside main XP.

**Explorer skill deliberately deferred to Phase 5** — it needs course/region discovery to exist before there's anything for it to detect.

266 backend tests total, all passing. Verified against the real docker compose stack: re-synced the connected account's real activity through the full pipeline — all 4 skills correctly earned the 150 XP baseline (no prior history yet), confirmed via direct DB inspection and the real `GET /api/v1/skills` endpoint. Frontend `SkillsPanel` (level + XP bar grid) confirmed rendering correctly via a real Playwright screenshot.

### Infrastructure / tooling notes worth remembering
- **Docker Desktop + WSL2 hot-reload gotcha**: Vite's dev server (and possibly uvicorn's `--reload`) doesn't reliably detect file edits made from the Windows side of the bind mount, even though the mount itself is live/correct. A `usePolling`/`WATCHFILES_FORCE_POLLING` fix was attempted but didn't fully resolve it for this project's Rolldown-based Vite. **Restart the frontend container after frontend edits** before verifying, rather than trusting hot-reload.
- All shell commands in this project are run through WSL Ubuntu (`wsl -d Ubuntu -- bash ...`), per user preference for Linux tooling over native PowerShell. Nested-quote commands are unreliable through the PowerShell→wsl.exe→bash chain (Windows argv parsing mangles embedded double quotes) — writing throwaway `.sh` scripts to the scratchpad directory and executing them by path is the reliable pattern.
- Playwright is now fully working for real browser verification (`sudo env "PATH=$PATH" npx --yes playwright@latest install-deps chromium` was the fix for nvm+sudo PATH issues).

## Current State (as of last update)
- Stack running via `docker compose up`: postgres, redis, backend (FastAPI + arq worker), frontend (Vite/React/TS) — all healthy.
- Real Garmin account connected (with MFA), real activity synced and generating real XP/leveling/skill data (currently main Level 2; all 4 skills at Level 1 with 150/400 XP).
- 266 backend tests passing.
- Frontend shows: login, level/XP bar, skills grid, Garmin connect/sync panel. No real visual design yet (expected — that's Phase 7).

## What's Next
- **Phase 5** — Courses & Regions (route matching, personalized course difficulty/mastery, Home Base + region naming). Also unlocks the deferred Explorer skill.
- **Phase 2.5** — Manual FIT/GPX import fallback (insurance against Garmin breaking again) — still open, order relative to Phase 5 not yet decided.

Then Phases 5 (Courses & Regions), 6 (Goals), 7 (gamified frontend polish), 8 (auto-sync-on-load + weather), 9 (cloud-deploy prep) per the original roadmap above.
