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

The app runs on Render as two independent copies of the same
infrastructure, each defined by a [Render Blueprint](https://render.com/docs/blueprint-spec)
at the repo root:

- **dev** (`render.yaml`): `snake-arena` deploys from `main` and
  `snake-arena-staging` deploys from `staging`. Both share the
  `snake-arena-db` Postgres database.
- **production** (`render.production.yaml`): `snake-arena-prod` deploys
  from the `production` branch and has its own `snake-arena-prod-db`
  database. Nothing done in dev reaches production data.

A change goes `staging` → `main` (dev) → `production`, each step a
fast-forward to a commit already verified in the previous environment.
See `_docs/release-process.md`.

Render's free tier allows one active database per workspace, so the
production Blueprint is applied in a separate Render workspace (or one
of the databases goes on a paid plan). Setup steps, including the
GitHub variables the Deploy workflow needs (`RENDER_URL_STAGING`,
`RENDER_URL_DEV`, `RENDER_URL_PROD`), are in `_docs/deployment.md`.

The free plans in both Blueprints are dev-only (Render expires free
databases after a limited period, and free web services spin down when
idle). Switch production's `plan` fields to paid plans for anything
long-lived. Tables are created automatically on first boot, and the
backend serves both the API and the built frontend from the one
service, same as the Docker Compose setup above.

### CI/CD

`.github/workflows/ci.yml` (**CI**) runs backend and frontend tests in
parallel, then builds and boots the real `docker-compose.yml` stack
(app + Postgres) and runs `integration-tests/` against it over HTTP —
signup, submit score, leaderboard, SPA fallback — exercising the real
database and static-file serving that the in-process unit tests don't
touch.

Render auto-deploys every push to `staging`, `main` and `production`
independently of this workflow — Render has no GitHub OIDC support, only
a static API key/deploy-hook secret, so deploys aren't driven from CI.
Instead, once CI passes for a push to one of those branches,
`.github/workflows/deploy.yml` (**Deploy**) waits for that
environment's live deploy to report healthy and then runs the same smoke
suite against it (via the `RENDER_URL_STAGING`/`RENDER_URL_DEV`/`RENDER_URL_PROD`
repo variables), so a broken deploy shows up as a failed Deploy run rather
than going unnoticed. Note this writes a uniquely-named `ci-smoke-*`
user and score into that environment's leaderboard on every run.

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
