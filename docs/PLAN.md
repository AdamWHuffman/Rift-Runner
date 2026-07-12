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

### Core Algorithm: Course Leveling — ✅ built, see Progress Log

### Home Base & Region Naming — ✅ built, see Progress Log

Real generated names confirmed for the Arlington/DC area so far: *The Millrace Reaches* (riverlands, near the Potomac/Four Mile Run). Planning-time illustrative examples for reference: *The Ridgeway Spires*, *Potomac's Landing*, *Glasshaven Heights*, *The Fourmile Reaches*, *Ridgemont Crossing*.

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
2.5. Manual import fallback — 📋 backlogged (not urgent while Garmin sync works)
3. Core XP & main leveling — ✅ complete
4. Skills — ✅ complete (all 5, including Explorer)
5. Courses & Regions — ✅ complete
6. Goals — ✅ complete
7. Gamified frontend polish — ✅ complete (core dashboard experience; onboarding wizard & settings screen deferred)
8. Auto-sync-on-load + weather — ✅ complete
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

### Phase 5 — Courses & Regions ✅ complete & verified
`garmin_sync/adapter.py` gained `fetch_activity_polyline()` (a real, separate per-activity Garmin API call for full GPS points — confirmed shape: `geoPolylineDTO.polyline`, best-effort, never blocks sync). `region_engine/` (geocode.py: Nominatim address→coords + Overpass best-effort theme detection with a short timeout and graceful fallback; namegen.py: deterministic fantasy name generator — SHA-256-seeded rather than Python's `hash()`, which is per-process randomized and would have silently broken "same place → same name" across restarts; region_service.py: find-or-create within a 10km radius, shared by home-base setup and auto-created course regions). `course_engine/` (matching.py: geohash-bucketed candidates + polyline-resampling similarity check; difficulty.py: personalized `difficulty_rating_at_discovery`, verified against the plan's own worked example numbers exactly; course_service.py: orchestrates matching/region-creation/frozen-difficulty/mastery-leveling, reusing `xp_engine.leveling` again, with repeat-run decay floored at 0.3x). `course_difficulty_multiplier` (stubbed since Phase 3) and the Explorer skill (deferred since Phase 4) are both wired in for real now. New `POST/GET /regions/home-base` and `GET /courses` endpoints; frontend `HomeBasePanel` + `CoursesPanel`.

315 backend tests total, all passing (46 new this phase). Verified against the real docker compose stack end-to-end: re-synced the connected account's real activity through the complete pipeline — auto-created a real region ("The Millrace Reaches", correctly classified riverlands near the Potomac/Four Mile Run), discovered a course named after the real Garmin activity ("Arlington County Walking"), computed a real personalized difficulty rating (39), awarded course mastery XP and Explorer skill XP on first discovery. Verified all new endpoints via real HTTP, including that submitting "Arlington, VA" as a home base through a live browser correctly reused the same auto-created region instead of creating a duplicate (the 10km-radius reuse logic working as designed). Screenshot-confirmed via Playwright.

### Phase 6 — Goals ✅ complete & verified
This phase was explicitly the least-defined part of the original plan, so per the user's direction ("stop and ask me" if there are open questions), implementation paused for clarification before any code was written. Four questions were asked and answered before proceeding:

1. **Goal taxonomy** — the user's actual current goal ("improve health, run/walk more, sustain longer runs, but stay in low HR zones to prevent injury") didn't cleanly fit the original plan's three goals, so a **4th goal, `base_building`, was added** rather than overloading `general_health`.
2. **HR zone strictness** — the user corrected the initial framing: zones 1-3 are all aerobic and should all be rewarded reasonably; only zones 4-5 (anaerobic) should be de-emphasized, and even then only de-emphasized, not zeroed out, since brief anaerobic bursts are healthy. All 4 goals' `zone_weight_targets` were tuned around this real exercise-science distinction rather than a flat "low HR good, high HR bad" rule.
3. **Multi-goal** — single active goal per user at a time (not multiple simultaneous goals), switchable, with `user_goal_history` tracking every activation/deactivation so past XP stays meaningful even after switching.
4. **Skill/PR dampening** — the user was explicit that skills (including Speed) and the PR bonus should **not** be dampened by the active goal ("skills are just nice to have... speed generally will increase with any training"). Only the main-XP `goal_alignment` multiplier is goal-aware; this matches the original plan's design exactly, so no changes were needed there.

Built: `Goal`/`UserGoalHistory` models, `users.active_goal_id`, `xp_transactions.goal_id_at_time` (append-only — every XP transaction records which goal was active when it was earned, so switching goals never retroactively changes history's meaning), migration `0007_goals`. `config_data/goals.yaml` seeds all 4 goals with real target HR-zone-time distributions. `formulas.goal_alignment_multiplier()` compares actual zone-time fractions to the active goal's target vector via L1 distance, mapped to a 0.7x-1.3x multiplier (neutral 1.0x when no HR data or no active goal). `goal_engine/goal_service.py` handles switching (closes out the previous open history row, opens a new one). Wired into `calculator.process_activity()` and `sync_service`. `GET /goals`, `GET /goals/active`, `POST /goals/active` endpoints; frontend `GoalsPanel` (card grid, click to switch, active goal highlighted).

326 backend tests total, all passing (11 new this phase). Verified against the real docker compose stack: migration applied, all 4 goals seeded and confirmed via a real `GET /api/v1/goals` call; frontend goal picker confirmed working via a real Playwright screenshot against a throwaway test account (clicking "Base Building" correctly highlighted it as active, no console errors); active goal set to `base_building` on the real connected account via the real API (a sensible real default matching the user's actual stated fitness goal, left in place rather than reverted); goal-alignment multiplier verified against the real account's real synced activity's real HR-zone data (1.20x for a zone-2/3-heavy walk against the base_building target, computed identically by the pure formula and the full calculator, with `goal_id_at_time` correctly linked) via a dry-run that was rolled back to avoid persisting duplicate XP.

### Phase 7 — Gamified Frontend Polish ✅ complete & verified
The original plan named a "rogue RuneScape" visual direction, but that was always a placeholder for "make it feel fun," not a locked spec — so before building anything real, this phase ran an extended design-exploration loop using standalone HTML/CSS/JS mockups published as Artifacts (self-contained, no build step, safe to throw away), so the user could react to full visual directions before any React code was touched.

**Directions explored, in order, each rejected or refined based on direct feedback:**
1. Dark fantasy / gilded-frame MMO look (Cinzel/Pirata One, obsidian-and-gold) — rejected as "too dark."
2. Bright flat "cutesy mobile game" (Fredoka/Nunito, candy colors) — never even shown; superseded before publishing by a same-session pivot to a new brief.
3. **"Whimsified Reality"** — a light storybook lens over real places (Fraunces/Karla, warm cream/moss/gold/coral palette), built around a real mechanic: real observed features (a cobwebbed tunnel, a creek crossing, a flight path overhead) get reinterpreted as whimsical names ("Spider Cave," "Merrow's Ford") rather than an invented fantasy map. This tested well ("definitely closer") but went through several refinement rounds — a fog-of-war exploration map was prototyped then explicitly deferred ("that's a later design"), an attempt to add a recurring mascot character and small creature illustrations was tried and then explicitly rejected ("do not use them in the design").
4. A colorful "video game feel" pass (Baloo 2, saturated toy colors, screen-shake/confetti-cannon level-up) — tried per explicit request to push the game-juice further, but the user preferred the calmer Whimsified Reality version overall ("I actually like this less, go back to previous").
5. An "open-world quest board" pivot (themed biome pockets — Egyptian/Space/Pirate/Prehistoric/Jungle/Ice/Medieval/Western — each a toy-diorama "globe," a Quest Log reframing of the reskinning mechanic, objective checklists) — well-received as a concept and pushed further with real CC0 photography sourced from Kenney.nl for 4 of the 8 biomes, but the stock-photo style itself didn't land, and the biome/quest-zone concept was ultimately **backlogged** as a bigger feature than current scope (it doesn't map onto the backend's real region model, which generates one region per real GPS area, not a curated set of admin-picked biome themes).

**Final direction shipped**: Whimsified Reality (direction 3, pre-character-additions) — Fraunces (display/voice) + Karla (body) via `@fontsource`, warm cream-to-mist gradient background, moss/gold/coral/sky/plum/teal accent palette, soft asymmetric-radius cards, no illustrated characters, gentle glow-ring level-up (no screen shake, no mascot).

**Built for real** (not mockups — actual wired React components against actual backend data):
- Global theme (`index.css`, `App.css`) replacing the Vite scaffold defaults entirely.
- `LevelUpCelebration.tsx` — full-screen overlay, glow rings, a hand-rolled canvas particle system (soft glowing motes, not a confetti library — this reuses code proven out during the mockup phase rather than adding `canvas-confetti` as a dependency), a from→to level flip, and a **real event queue**: `sync_jobs.level_up_events` can contain multiple events (main + several skills + course) from one sync, and the component walks through them one at a time on tap/click, exactly matching the original plan's "queued if multiple fire at once" requirement. Verified firing two queued events in sequence via a temporary dev-only trigger button (added, screenshotted, then removed before commit).
- `SyncOverlay.tsx` — full-screen spinner shown between `sync/trigger` and job completion.
- `ActivityFeed.tsx` + new backend `GET /api/v1/activities` endpoint (`app/schemas/activity.py`, `app/api/v1/routers/activities.py`) — an expandable accordion list of recent activities; expanding one reveals the exact same transparent XP breakdown (base XP, each named multiplier, final XP) that `xp_transactions` has stored since Phase 3, fulfilling the plan's "doubles as an algorithm-debugging view" goal. Verified against the real account: correctly showed a historical activity's `goal_alignment: 1.0` because that activity was synced *before* the real account's goal was set — direct visual proof the append-only ledger design is working (old transactions never get retroactively rewritten).
- `SkillsPanel.tsx`, `CoursesPanel.tsx` (now grouped under region banners), `GoalsPanel.tsx`, `HomeBasePanel.tsx`, `GarminPanel.tsx`, `LoginForm.tsx` — all restyled to the shared design system; no behavior changes.
- Deliberate deviation from the original plan's tech list: **no Framer Motion, no `canvas-confetti`** — the mockup phase proved hand-rolled CSS keyframes + a small canvas particle loop achieve the same effect with zero added dependencies, so that's what shipped.

**Explicitly deferred/backlogged** (per direct instruction to focus on core functionality rather than open-ended scope): the themed biome/quest-zone system from direction 5; a dedicated multi-step onboarding wizard (today's flow — connect Garmin / set home base / pick goal — still works, just isn't sequenced as a guided tour); a separate Settings screen (Garmin reconnect already lives inline in `GarminPanel`; a "units" preference doesn't exist on the backend yet).

326 backend tests still passing (one new endpoint, no service-layer logic to unit test — verified via real HTTP against the Docker stack instead, matching this project's established convention of testing routers by real call rather than `TestClient`). Verified end-to-end via Playwright screenshots against a throwaway account: full dashboard render (no console errors), the level-up celebration firing and correctly advancing through a 2-event queue, and the activity accordion expanding to show a real multiplier breakdown. The real connected account's `GET /api/v1/activities` was also hit directly and returned correct real data.

**Follow-up: real course maps.** The initial Phase 7 pass shipped a course *list* but no route visual, which the user flagged immediately as a real gap — Garmin/Strava-style course pages show an actual picture of the route, not just stats. Fixed same-session: `CourseProgressResponse` now includes `polyline` (the course's real `canonical_polyline`, already captured since Phase 5 — 695 real GPS points for the one real discovered course), and a new `CourseMap` component (`leaflet` + `react-leaflet`, CartoDB Positron light basemap, no API key required) renders it as a real interactive map — actual streets and the Potomac riverfront visible, not a stylized illustration — with the route drawn as a polyline and start/end circle markers.

The user flagged forward-looking context worth preserving here: **this map is intended to eventually carry the backlogged themed-biome reskinning** (see Backlog below), so the basemap choice (clean/minimal, not busy/branded) and the marker/route styling (vector `CircleMarker`s, not Leaflet's default icon-image markers, which have a well-known bundler asset-path papercut and wouldn't match the app's look anyway) were both chosen to leave room for that without committing to it now. As a small, real, non-overbuilt down payment on that vision, the route/marker colors are keyed off the region's actual `theme` field (`riverlands`/`highlands`/`greenwood`/`metropolis` — real data computed by `region_engine` since Phase 5, not the backlogged curated fantasy biomes), reusing the app's existing design tokens. The user also confirmed that fully automated landmark-based theming (e.g. auto-detecting "this tunnel has spiders") isn't realistic — future biome theming will be hand-designed for specific real locations, starting with Arlington, VA, as a later phase, not attempted now.

Verified against real data: `GET /api/v1/courses` confirmed returning all 695 real polyline points for the real "Arlington County Walking" course with `region_theme: "riverlands"`. Visually verified via Playwright by seeding a throwaway account with a course reusing that same real polyline under a `highlands`-themed region — the map rendered a real recognizable stretch of Arlington/the Potomac with a correctly plum-colored route and start/end markers, zoom controls, and proper OpenStreetMap/CARTO attribution, no console errors. Test data cleaned up afterward.

**Follow-up: click to expand.** The thumbnail was flagged as too small. Clicking it now opens a much larger interactive map in a modal (full pan/zoom, close via backdrop click/×/Escape); the thumbnail itself became a fully static, non-interactive preview (all Leaflet interaction handlers off, `pointer-events: none` on the tile layer) wrapped in a real `<button>` for accessibility, with a "View larger" hint on hover.

**Real bug found and fixed: the thumbnail rendered on top of the expanded modal.** Root cause, confirmed by the user in their real browser: Leaflet's internal panes use z-index values up to ~700 (tile pane 200, overlay 400, marker 600...), but Leaflet's own `.leaflet-container` only sets `position: relative` on itself with no z-index -- which does **not** establish a new CSS stacking context. Without one, those internal z-index values compare directly against page-level siblings instead of staying contained, so the thumbnail's tile pane (200) rendered above the modal overlay (110). This was chased for a while as a suspected "headless-Chromium screenshot artifact" (automated screenshots showed a torn-looking map background that persisted through several unrelated fix attempts -- disabling StrictMode, disabling the pan animation, switching to a manual synchronous `fitBounds()` call -- and direct DOM inspection proved the tile grid's own math was pixel-perfect), until the user's real-browser report reframed it correctly as a z-order bug, not a rendering bug. Fixed with `isolation: isolate` on the thumbnail wrapper (properly contains Leaflet's internal z-index scheme) plus bumping the modal to z-index 1000 as a second line of defense. The same fix was applied preemptively to `LevelUpCelebration` and `SyncOverlay`, since either could in principle fire while a course map thumbnail is on screen underneath and hit the identical bug.

### Phase 8 — Auto-Sync-on-Load + Weather ✅ complete & verified
Two pieces named together in the original plan, both genuinely small once investigated:

**Auto-sync-on-load.** The debounce logic this needed (`DEBOUNCE_WINDOW = timedelta(minutes=2)` in `sync.py`, returning the in-flight or most-recently-completed job instead of enqueueing a duplicate) turned out to already exist, built back in Phase 2 in anticipation of this. All that was missing was the frontend actually calling it automatically: `GarminPanel` now fires `handleSync()` once on mount (guarded by a `useRef` against React StrictMode's dev-only double-effect-invoke) whenever the user is logged in with a connected Garmin account, reusing the exact same trigger/poll/celebrate pipeline the manual "Sync now" button already used. A failed sync (trigger throws, or the polled job comes back `status: "failed"`) now surfaces a small dismissing `Toast` ("Could not reach Garmin — showing cached data") instead of just failing silently, per the original plan's UX spec.

**Weather (heat index).** New `weather/open_meteo.py` service, matching `region_engine/geocode.py`'s established best-effort pattern exactly (sync `httpx.get`, short timeout, broad exception handling, `None` on any failure -- never blocks sync). Uses Open-Meteo's standard forecast endpoint with `past_days` rather than its separate historical/archive endpoint, since the archive endpoint lags a few days behind real time and would miss "synced this morning" activities, which are the common case here. Heat index computed via the standard NWS Rothfusz regression (heat index equals air temperature below 80°F/26.7°C, per NWS convention). New `formulas.heat_multiplier()`: neutral below the 80°F "Caution" threshold, scaling linearly up to +25% at the 104°F/40°C "Danger" threshold, capped beyond that -- mirroring `goal_alignment`'s "neutral when the input doesn't apply" shape rather than ever penalizing comfortable weather. Activity gained `temperature_c`/`humidity_pct`/`heat_index_c` columns (migration `0008_weather`, all nullable -- same graceful-degradation contract as everything else best-effort in this schema); `sync_service.py` looks the weather up once per new activity (using its GPS start point + start time) right after creation and before XP calculation, so `heat_index_c` is available for `calculator.process_activity()` to read directly off the activity, matching how `hr_seconds_in_zone` is already read rather than threaded through as an extra parameter. `ActivityFeed` shows the real temperature and (when different) the heat-adjusted "feels like" figure inline in each activity's summary line, plus a `× Heat` row in the expanded breakdown alongside the other multipliers.

12 new backend tests (heat_multiplier's threshold/scaling/cap behavior; the weather service's real Open-Meteo response shape, hour-matching, and every failure path, mocked the same way `test_geocode.py` mocks Nominatim/Overpass; calculator wiring). 338 backend tests total, all passing. Verified against real data end-to-end: hit the real Open-Meteo API directly against the real connected account's real activity location/time (Arlington, VA, July 11) and got back a real temperature (25.4°C/78°F, 87% humidity) -- below the heat bonus threshold, so neutral, which is itself a correct result, not a null one. Backfilled that real activity's weather columns (a real, useful write, not just a test) and confirmed via a real `GET /api/v1/activities` call that the data flows through correctly -- and that the *stored* `xp_transactions` row correctly has no `"heat"` key at all, since that transaction was written before this phase existed, which is the append-only ledger design working exactly as intended (old transactions are never rewritten when the formula gains a new factor). Visually verified the full UI (temperature/feels-like line, heat multiplier breakdown row) via Playwright against a throwaway account seeded with a synthetic hot-weather activity (95°F/35°C, feels 103°F/39.4°C, heat multiplier 1.24x) -- rendered correctly, no console errors. Test data cleaned up afterward.

### Infrastructure / tooling notes worth remembering
- **Docker Desktop + WSL2 hot-reload gotcha**: Vite's dev server (and possibly uvicorn's `--reload`) doesn't reliably detect file edits made from the Windows side of the bind mount, even though the mount itself is live/correct. A `usePolling`/`WATCHFILES_FORCE_POLLING` fix was attempted but didn't fully resolve it for this project's Rolldown-based Vite. **Restart the frontend container after frontend edits** before verifying, rather than trusting hot-reload.
- All shell commands in this project are run through WSL Ubuntu (`wsl -d Ubuntu -- bash ...`), per user preference for Linux tooling over native PowerShell. Nested-quote commands are unreliable through the PowerShell→wsl.exe→bash chain (Windows argv parsing mangles embedded double quotes) — writing throwaway `.sh` scripts to the scratchpad directory and executing them by path is the reliable pattern.
- Playwright is now fully working for real browser verification (`sudo env "PATH=$PATH" npx --yes playwright@latest install-deps chromium` was the fix for nvm+sudo PATH issues).
- **Any new full-screen overlay/modal needs `isolation: isolate` (and a z-index comfortably above ~700)** if a Leaflet map could ever be visible underneath it. Leaflet's own container doesn't establish a CSS stacking context for its internal panes (z-index up to ~700), so without `isolation: isolate` on the *lower* element containing the map, those panes leak out and can render above higher-z-index overlays that don't also defend against it. `CourseMap`, `LevelUpCelebration`, `SyncOverlay`, and `Toast` all already have this; keep it in mind for anything new in the same family.

## Current State (as of last update)
- Stack running via `docker compose up`: postgres, redis, backend (FastAPI + arq worker), frontend (Vite/React/TS) — all healthy.
- Real Garmin account connected (with MFA), real activity synced and generating real XP/leveling/skill/course/region/weather data (main Level 2; all 5 skills tracking progress; 1 real course discovered in a real auto-named region, with a real course map).
- 4 goals seeded; real account's active goal set to `base_building`, matching the user's actual stated fitness goal (low-injury-risk aerobic base building).
- 338 backend tests passing.
- Frontend has a real visual design system ("Whimsified Reality" — Fraunces/Karla, warm storybook palette) applied across every screen: level/XP hero plaque, home base, goal picker, skills grid, region-grouped courses with real clickable-to-expand OpenStreetMap route maps, an activity log with an expandable transparent XP breakdown (now including real weather/heat context), Garmin connect/sync (now automatic on page load, debounced, with a cached-data toast on failure), and a real animated level-up celebration (queued multi-event, canvas particles, no added dependencies) triggered off real sync results.

## What's Next
- **Phase 9** — Cloud-deploy prep.

## Backlog (not currently scheduled)
- **Phase 2.5 — Manual FIT/GPX import fallback.** Insurance against Garmin's unofficial API breaking again (upload a `.fit`/`.gpx` export as a second ingestion path, tagged `source=manual_upload`, into the same `activities` table). Not urgent while Garmin sync is working; revisit if it breaks or before a public launch.
- **Themed biome/quest-zone system, reskinning the real course map.** Explored during Phase 7's design phase (Egyptian/Space/Pirate/Prehistoric/Jungle/Ice/Medieval/Western pockets, a Quest Log framing of the environmental-reskinning mechanic). Well-received as a concept but needs real backend design work first — it doesn't map onto the current one-region-per-real-place model. The user has confirmed the eventual approach: this can't be automated (no reliable way to auto-detect "this tunnel has spiders" from GPS data alone), so it will mean hand-designing themed regions for specific real places, starting with Arlington, VA. The real `CourseMap` (Leaflet + OSM, shipped in Phase 7) was deliberately built with this in mind — clean minimal basemap, vector markers, region-theme-aware coloring already — as the surface this would eventually skin.
- **Onboarding wizard.** Sequence the existing connect-Garmin/home-base/goal-pick flow into a guided first-run tour instead of showing everything at once.
- **Settings screen.** Garmin reconnect (already inline in `GarminPanel`) plus a units preference, which doesn't exist on the backend yet.
