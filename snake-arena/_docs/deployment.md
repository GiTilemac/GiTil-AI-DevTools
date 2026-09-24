# Deploying Snake Arena

Snake Arena ships as **one Docker image** that serves both the API and
the built frontend on port 8000. The only thing it needs is a database,
set through `DATABASE_URL`. That same image runs locally under Docker
Compose and on Render.

For how a change moves from staging to production, see
[release-process.md](release-process.md).

## The image (`Dockerfile`)

It's a two-stage build:

1. **`frontend-build`** (`node:22-alpine`) runs `npm ci` and
   `npm run build` with `VITE_API_BASE_URL=""`, so the client calls the
   API on the same origin using relative paths.
2. **`backend`** (`python:3.11-slim`) installs the backend dependencies
   with `uv sync --frozen --no-dev`, copies `backend/app`, and copies
   the built frontend into `./static`. It then runs
   `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

The backend serves `/assets` and falls back to the SPA for app routes
when `static/` is present. The health endpoint is `GET /health`, which
returns `{"status": "ok"}`.

## Configuration

| Variable       | Default                          | Notes                                              |
|----------------|----------------------------------|----------------------------------------------------|
| `DATABASE_URL` | `sqlite:///./snake_arena.db`     | Use `postgresql+psycopg://…` for Postgres. Plain `postgres://` or `postgresql://` URLs, like the ones Render provides, are rewritten to use psycopg automatically. |

The schema is created on startup (`Base.metadata.create_all()` in
`backend/app/store.py`). There's no migration step, but existing tables
are never altered either. See *Database changes* in
[release-process.md](release-process.md).

## Local: Docker Compose

`docker-compose.yml` runs two services:

- `app`: built from the `Dockerfile`, with port `8000:8000` published.
- `db`: `postgres:16-alpine`. Its data lives in the `pg-data` volume and
  it has a `pg_isready` healthcheck. `app` waits until `db` is healthy.

```bash
docker compose up --build        # http://localhost:8000
docker compose down              # stop, keep data
docker compose down -v           # stop and delete the database volume
```

The app reaches Postgres at the hostname `db` on port `5432`. The
credentials (`snake`/`snake`) are for development only.

## Render

`render.yaml`, at the repo root, is a Render Blueprint:

| Service               | Branch    | Plan | Health check |
|-----------------------|-----------|------|--------------|
| `snake-arena`         | `main`    | free | `/health`    |
| `snake-arena-staging` | `staging` | free | `/health`    |
| `snake-arena-db` (Postgres) | –   | free | –            |

Both web services build `snake-arena/Dockerfile` and get `DATABASE_URL`
from `snake-arena-db`.

### First-time setup

1. Push the repo to GitHub, including the `staging` branch.
2. In Render, go to **New → Blueprint**, pick the repo, and click
   **Apply**. Render creates the database and both services.
3. In GitHub, go to **Settings → Secrets and variables → Actions →
   Variables** and set `RENDER_URL_STAGING` and `RENDER_URL_PRODUCTION`
   to each service's base URL. The Deploy workflow's verify jobs fail until these are
   set.

### How deploys happen

- Render **auto-deploys every push** to `main` or `staging`. The CI
  workflow doesn't start or gate the deploy, because Render only
  supports a static API key or deploy hook, not GitHub OIDC.
- Once the **CI** workflow (`.github/workflows/ci.yml`) passes for that
  push, the **Deploy** workflow (`.github/workflows/deploy.yml`) starts.
  Its `verify-*-deploy` job waits up to about 10 minutes for `/health`
  and then runs `integration-tests/` against the live URL. That way a
  broken deploy shows up as a failed run.
- Deploy is triggered by `workflow_run`, and GitHub only uses the copy
  of `deploy.yml` on `main`. A change to that file only takes effect
  once it's on `main`, even for staging runs.
- Setting `autoDeployTrigger: checksPass` on the services in
  `render.yaml` would make Render wait for green GitHub checks before
  deploying. It isn't enabled yet.

### Caveats

- **Shared database.** Staging and production use the same Postgres,
  because the free tier allows only one database. Staging users, scores
  and CI `ci-smoke-*` entries all appear on the production leaderboard.
  To isolate them, put the database on a paid plan and add a second
  database for staging.
- **Free plans.** Web services spin down when idle, so the first request
  after a while is slow. Free databases expire after a limited period.
  Switch the `plan` fields to a paid plan for anything long-lived.
- **`/leaderboard` on a hard refresh** returns the API's JSON instead of
  the page, because the frontend route and the API endpoint share a
  path. See the README's *Known limitation* section.

## Rolling back

In the Render dashboard, open the service → **Deploys** → the last good
deploy → **Rollback**. This reuses the old build, so there's no rebuild.
Rolling back **turns off auto-deploy** for that service. Turn it back on
once the fix has gone through staging.
