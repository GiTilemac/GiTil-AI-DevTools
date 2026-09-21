# Snake Arena — Context Summary

Snapshot of project state for agents picking up work here. This is a status
snapshot, not a spec — for the original requirements/architecture rationale
see `plan.md` and `spec.md` in this directory; for stable working
conventions see `../AGENTS.md`. Update this file (not those) as state
changes; it decays fast and should be refreshed by whichever agent next
does substantial work.

**As of:** 2026-09-14 (commit `552242e`, latest on `main`)

## Current state

Full stack is built and wired end-to-end:

- **Frontend** (`frontend/`): React + TypeScript + Vite SPA. Game engine,
  auth, leaderboard, and a "watch a live bot" spectator screen. All
  "backend" calls go through the single facade `frontend/src/api/backendClient.ts`
  — never bypass it.
- **Backend** (`backend/`): FastAPI, implementing the contract in
  `openapi.yaml`. Users/tokens/leaderboard persist via SQLAlchemy + SQLite
  (`DATABASE_URL`, defaults to a local `snake_arena.db` file). The
  always-on demo bot behind `/watch/live` (SSE) stays in-memory/ephemeral
  by design — it's simulation state, not user data.
- **`backendClient.ts` talks to the real backend over HTTP/SSE** (fetch +
  EventSource), not a mock. Bearer tokens are kept in memory only (never
  localStorage), so a page reload still starts logged out — a deliberate
  product decision, not a gap.

⚠️ `AGENTS.md` and `_docs/plan.md` predate this wiring and still describe
the frontend as talking to a mock / no real backend existing. Trust this
file and the commit log over those two on that point until someone updates
them.

## Test status (as verified in the last commit)

- Backend: 39/39 pytest passing (`uv run pytest` from `backend/`)
- Frontend: 74/74 Vitest passing, typecheck clean, build clean
  (`npm run test:run` / `npm run typecheck` / `npm run build` from `frontend/`)
- Frontend tests now mock at the network boundary (`frontend/src/test/mockServer.ts`
  stubs `fetch`/`EventSource` against the same contract the real backend
  implements) rather than mocking `backendClient` itself — exercises real
  request/response handling.

## Recent history (newest first)

1. `552242e` — Added backend tests (self-collision, direction-reversal,
   bot-restart-countdown, double-logout-rejected) and frontend tests
   (routing table, "fresh load always logged out", mode-lock-while-running)
   for spec behavior that existed but wasn't exercised yet.
2. `3af7bc0` — Replaced the in-memory backend store with SQLAlchemy +
   SQLite (`app/db.py`, `app/db_models.py`). Store methods are sync (FastAPI
   runs them in its thread pool so the `/watch/live` SSE event loop isn't
   blocked). `UsernameTakenError` added as a race-safety net behind the DB's
   unique constraint. No SQLite-specific SQL outside `db.py`'s engine setup —
   swapping to Postgres later (`postgresql+psycopg://...`) should be a
   `DATABASE_URL` change only.
3. `2adc429` — Switched `backendClient.ts` from the in-memory mock to real
   `fetch`/`EventSource` calls (see above).
4. `ade1906` — Added `openapi.yaml` and the initial FastAPI backend
   (in-memory store at the time), implementing the contract implied by the
   frontend's original mock.
5. `b17ffe3` / `5cf4289` / `0a80523` — Initial frontend build: game engine,
   mocked multiplayer backend, docs, moved into `frontend/`.

## Known gaps / explicitly out of scope

- No Postgres (or other non-SQLite) backend configured yet — the migration
  path exists (`DATABASE_URL`) but hasn't been exercised against a second
  engine.
- No lobby of multiple spectatable players — one always-on deterministic
  bot stands in for "watch a live player" (per original scoping decision).
- No auth session persistence across reloads — deliberate, not a bug.
- No CI config observed in the repo — tests are run manually per the
  commands above.

## Commands

- Backend (from `backend/`): `uv sync`, `uv run uvicorn app.main:app --reload`,
  `uv run pytest`
- Frontend (from `frontend/`): `npm run dev`, `npm run test:run`,
  `npm run typecheck`, `npm run build`
