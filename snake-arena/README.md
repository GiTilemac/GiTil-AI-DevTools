# Snake Arena

An interactive Snake game with two play modes, plus a full multiplayer
surface: accounts, a leaderboard, and watching another player currently in
a game. The frontend (`frontend/`, React + TypeScript + Vite) talks to a
real backend (`backend/`, FastAPI + SQLAlchemy, SQLite by default or
Postgres) over HTTP/SSE through a single facade,
`frontend/src/api/backendClient.ts`.

For local frontend/backend development (without Docker), see
[`frontend/README.md`](frontend/README.md) and
[`backend/README.md`](backend/README.md). For the full spec and current
project state, see [`_docs/`](_docs/).

## Running with Docker

`docker-compose.yml` (repo root) runs the app as two services: `app` (the
`Dockerfile` image — builds the frontend with Node, then copies the built
static files into a Python image that runs the backend, which serves both
the API and the frontend from a single container/port) and `db`
(`postgres:16-alpine`), wired together via `DATABASE_URL` with Postgres
data persisted in a named volume:

```bash
docker compose up --build
```

Then open http://localhost:8000. `docker compose down` stops both
containers and keeps the data volume; add `-v` to also delete it. The
Postgres credentials/db name in `docker-compose.yml` are dev-only
defaults — change them (and `DATABASE_URL` alongside them) for anything
beyond local use.

### Known limitation

The frontend's `/leaderboard` page and the backend's `GET /leaderboard`
API endpoint share the same path. Navigating there from within the app
works fine, but a hard refresh or direct link to `/leaderboard` hits the
API and returns JSON instead of the page. Every other route
(`/`, `/play`, `/login`, `/signup`, `/watch`) serves the app correctly on
a hard refresh.

## Deploying to Render

`render.yaml` (repo root) is a [Render Blueprint](https://render.com/docs/blueprint-spec)
that provisions this same Docker image as two environments, each a web
service plus its own managed Postgres database, wired together via
`DATABASE_URL`:

- **production** (`snake-arena` / `snake-arena-db`) — deploys from `main`.
- **staging** (`snake-arena-staging` / `snake-arena-db-staging`) —
  deploys from a `staging` branch, so a change can be verified against a
  real deploy before it's promoted to `main`.

Setup:

1. Push this repo to GitHub, including a `staging` branch (already done
   if you're reading this from the remote).
2. In the Render dashboard: **New > Blueprint**, pick this repo, and
   Render will pick up `render.yaml` from the repo root automatically.
3. Click **Apply**. Render builds `snake-arena/Dockerfile` for both
   services, creates both Postgres instances, and sets each service's
   `DATABASE_URL` to its own database's connection string.
4. In the CI/CD pipeline (see below), set the `RENDER_URL_STAGING` and
   `RENDER_URL_PRODUCTION` repo variables to each service's base URL
   (e.g. `https://snake-arena-staging.onrender.com`), so it can verify
   deploys automatically.

Promoting a change to production is a normal merge: land it on
`staging` first, confirm it on the staging URL, then merge/fast-forward
`staging` into `main`.

The free plans in `render.yaml` are dev-only (Render expires free
databases after a limited period, and free web services spin down when
idle) — switch the relevant `plan` fields to a paid plan for anything
long-lived. No other setup is required: tables are created automatically
on first boot, and the backend serves both the API and the built
frontend from the one service, same as the Docker Compose setup above.

### CI/CD

`.github/workflows/ci-cd.yml` runs backend and frontend tests in
parallel, then builds and boots the real `docker-compose.yml` stack
(app + Postgres) and runs `integration-tests/` against it over HTTP —
signup, submit score, leaderboard, SPA fallback — exercising the real
database and static-file serving that the in-process unit tests don't
touch.

Render's Blueprint auto-deploys on every push to `main`/`staging`
independently of this workflow — Render has no GitHub OIDC support, only
a static API key/deploy-hook secret, so deploys aren't driven from CI.
Instead, after a push to either branch, the pipeline waits for that
environment's live deploy to report healthy and then runs the same smoke
suite against it (via the `RENDER_URL_STAGING`/`RENDER_URL_PRODUCTION`
repo variables), so a broken deploy shows up as a failed CI run rather
than going unnoticed. Note this writes a uniquely-named `ci-smoke-*`
user and score into that environment's real leaderboard each run.

### Rolling back a bad deploy

Render keeps a deploy history per service and can [roll back](https://render.com/docs/rollbacks)
to any previous successful deploy, reusing its build artifact (fast, no
rebuild): open the service in the Render dashboard → **Deploys** tab →
find the last good deploy → **Rollback** → confirm.

Two things to know:

- Rolling back **automatically disables auto-deploy** for that service,
  so a bad commit can't immediately redeploy over your rollback. Fix the
  underlying issue and re-enable auto-deploy (or trigger a fresh manual
  deploy) once you're ready to move forward again.
- Database schema changes are safe to roll back past here: tables are
  created via `Base.metadata.create_all()` (backend/app/store.py), which
  only ever adds tables/columns, never drops them, so an older deploy
  keeps working against a newer database — it just ignores any columns
  it doesn't know about.
