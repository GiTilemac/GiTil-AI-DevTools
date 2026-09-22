# Snake Arena — Context Summary

Snapshot of project state for agents picking up work here. This is a status
snapshot, not a spec — for the original requirements/architecture rationale
see `plan.md` and `spec.md` in this directory; for stable working
conventions see `../AGENTS.md`. Update this file (not those) as state
changes; it decays fast and should be refreshed by whichever agent next
does substantial work.

**As of:** 2026-09-21 (commit `e679b41` on `main`, plus Postgres-support
changes described below still uncommitted as of this writing)

## Current state

Full stack is built and wired end-to-end, and containerized:

- **Frontend** (`frontend/`): React + TypeScript + Vite SPA. Game engine,
  auth, leaderboard, and a "watch a live bot" spectator screen. All
  "backend" calls go through the single facade `frontend/src/api/backendClient.ts`
  — never bypass it.
- **Backend** (`backend/`): FastAPI, implementing the contract in
  `openapi.yaml`. Users/tokens/leaderboard persist via SQLAlchemy
  (`DATABASE_URL`, defaults to a local `snake_arena.db` SQLite file).
  **Postgres is now also supported** — `psycopg[binary]` is a bundled
  dependency; point `DATABASE_URL` at `postgresql+psycopg://...` to use
  it. No code changes were needed for this: the store layer was already
  plain SQLAlchemy Core/ORM with no SQLite-specific SQL. Verified by
  running the full pytest suite and a live signup/restart/login smoke
  test against a real `postgres:16-alpine` container. The always-on demo
  bot behind `/watch/live` (SSE) stays in-memory/ephemeral by design —
  it's simulation state, not user data.
- **`backendClient.ts` talks to the real backend over HTTP/SSE** (fetch +
  EventSource), not a mock. Bearer tokens are kept in memory only (never
  localStorage), so a page reload still starts logged out — a deliberate
  product decision, not a gap.
- **`Dockerfile`** (repo root): multi-stage — builds the frontend with
  Node, then a Python image runs the backend, which also serves the
  built frontend (mounted static assets + a 404-based SPA fallback added
  to `backend/app/main.py`). One known limitation: the frontend's
  `/leaderboard` page and the backend's `GET /leaderboard` API share the
  same path, so a hard refresh there returns the API's JSON instead of
  the page (every other route is fine). See `../README.md`.
- **`docker-compose.yml`** (repo root): runs the combined app image
  alongside a `postgres:16-alpine` container, wired together via
  `DATABASE_URL`, data in a named volume. `docker compose up --build`
  from the repo root. Verified end-to-end (signup, container restart,
  login still works). Not currently the user's preferred way to run
  Postgres locally (see below) — may be redundant with it; ask before
  assuming both should be kept.
- **The user runs Postgres locally as a standalone container**, not via
  `docker-compose.yml`: `docker run -d --name interview-canvas-db -e
  POSTGRES_USER=snek -e POSTGRES_PASSWORD=snek -e POSTGRES_DB=snek -p
  5432:5432 -v snake-arena:/var/lib/postgresql/data postgres:16-alpine`
  (note: container/volume names don't match this project — likely reused
  from another project). Backend connects to it fine, verified live:
  `DATABASE_URL="postgresql+psycopg://snek:snek@127.0.0.1:5432/snek"` for
  `uv run uvicorn` on the host, or swap `127.0.0.1` for
  `host.docker.internal` when running the app in Docker instead.

`AGENTS.md` and `_docs/plan.md` were updated in `e679b41` and no longer
describe the frontend as mock-backed — safe to trust again.

## Test status (as verified in the last commit)

- Backend: 39/39 pytest passing (`uv run pytest` from `backend/`)
- Frontend: 74/74 Vitest passing, typecheck clean, build clean
  (`npm run test:run` / `npm run typecheck` / `npm run build` from `frontend/`)
- Frontend tests now mock at the network boundary (`frontend/src/test/mockServer.ts`
  stubs `fetch`/`EventSource` against the same contract the real backend
  implements) rather than mocking `backendClient` itself — exercises real
  request/response handling.

## Recent history (newest first)

0. *(uncommitted)* — Added Postgres support (`psycopg[binary]` dependency
   only, no code changes needed) and `docker-compose.yml` (app +
   Postgres, wired via `DATABASE_URL`). Both verified live against a real
   Postgres container, not just assumed to work.
1. `e679b41` — "Add docker stuff": multi-stage `Dockerfile`
   (Node build → Python runtime), SPA-fallback static serving added to
   `backend/app/main.py`, `.dockerignore`, root `README.md`. Updated
   `AGENTS.md` and `_docs/plan.md` to stop describing the frontend as
   mock-backed (see "known gaps" note above about those two files, which
   this commit resolved — the note is now historical).
2. `552242e` — Added backend tests (self-collision, direction-reversal,
   bot-restart-countdown, double-logout-rejected) and frontend tests
   (routing table, "fresh load always logged out", mode-lock-while-running)
   for spec behavior that existed but wasn't exercised yet.
3. `3af7bc0` — Replaced the in-memory backend store with SQLAlchemy +
   SQLite (`app/db.py`, `app/db_models.py`). Store methods are sync (FastAPI
   runs them in its thread pool so the `/watch/live` SSE event loop isn't
   blocked). `UsernameTakenError` added as a race-safety net behind the DB's
   unique constraint. No SQLite-specific SQL outside `db.py`'s engine setup —
   this is what made adding Postgres support later (item 0 above) a
   dependency-only change.
4. `2adc429` — Switched `backendClient.ts` from the in-memory mock to real
   `fetch`/`EventSource` calls (see above).
5. `ade1906` — Added `openapi.yaml` and the initial FastAPI backend
   (in-memory store at the time), implementing the contract implied by the
   frontend's original mock.
6. `b17ffe3` / `5cf4289` / `0a80523` — Initial frontend build: game engine,
   mocked multiplayer backend, docs, moved into `frontend/`.

## Known gaps / explicitly out of scope

- The frontend's `/leaderboard` page and the backend's `GET /leaderboard`
  API endpoint share the same path — see the Dockerfile bullet above.
  Fixing it properly means prefixing API routes (e.g. `/api/leaderboard`),
  which touches `openapi.yaml`, `backendClient.ts`, and several backend
  tests; nobody has done that yet.
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
