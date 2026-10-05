# Deploying Snake Arena

Snake Arena ships as **one Docker image** that serves both the API and
the built frontend on port 8000. The only thing it needs is a database,
set through `DATABASE_URL`. That same image runs locally under Docker
Compose and on Render.

For how a change moves from dev to production, see
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

There are two independent copies of the infrastructure, each its own
Render Blueprint at the repo root:

| Environment | Blueprint                | Service               | Branch       | Database              |
|-------------|--------------------------|-----------------------|--------------|-----------------------|
| Dev         | `render.yaml`            | `snake-arena`         | `main`       | `snake-arena-db`      |
| Dev         | `render.yaml`            | `snake-arena-staging` | `staging`    | `snake-arena-db`      |
| Production  | `render.production.yaml` | `snake-arena-prod`    | `production` | `snake-arena-prod-db` |

Every service builds `snake-arena/Dockerfile`, runs on the free plan,
uses `/health` as its health check, and gets `DATABASE_URL` from its
own environment's database. Dev and production share nothing: separate
services, separate databases, separate data.

The dev service names are unchanged from when `render.yaml` was the
only Blueprint, because Render identifies Blueprint services by name.
Renaming them would create new services and leave the old ones behind.

### First-time setup

Dev (`render.yaml`) is already applied. For production:

1. Create the `production` branch from the commit currently deployed
   from `main` and push it:

   ```bash
   git fetch origin
   git push origin origin/main:refs/heads/production
   ```

2. In Render, switch to (or create) a **separate workspace** for
   production. The free tier allows only one active Postgres database
   per workspace, and dev's database already uses it. To keep both in
   one workspace, put one of the two databases on a paid plan instead.
3. Go to **New → Blueprint**, pick the repo, set **Blueprint path** to
   `render.production.yaml`, and click **Apply**. Render creates
   `snake-arena-prod-db` and `snake-arena-prod`. Tables are created on
   first boot.
4. In GitHub, go to **Settings → Secrets and variables → Actions →
   Variables** and set:

   | Variable             | Value                                  |
   |----------------------|----------------------------------------|
   | `RENDER_URL_STAGING` | dev staging service URL (unchanged)    |
   | `RENDER_URL_DEV`     | `snake-arena` service URL              |
   | `RENDER_URL_PROD`    | `snake-arena-prod` service URL         |

   Delete the old `RENDER_URL_PRODUCTION` variable; it pointed at the
   service that is now dev, and nothing reads it any more. The Deploy
   workflow's verify jobs fail until their variable is set.

Production starts with an empty database. Dev data (users, scores) is
not copied over.

### How deploys happen

- Render **auto-deploys every push** to `staging`, `main` (dev) and
  `production`. The CI workflow doesn't start or gate the deploy,
  because Render only supports a static API key or deploy hook, not
  GitHub OIDC.
- Once the **CI** workflow (`.github/workflows/ci.yml`) passes for that
  push, the **Deploy** workflow (`.github/workflows/deploy.yml`) starts.
  Its `verify-staging-deploy`, `verify-dev-deploy` or
  `verify-production-deploy` job waits up to about 10 minutes for
  `/health` and then runs `integration-tests/` against the live URL.
  That way a broken deploy shows up as a failed run.
- Deploy is triggered by `workflow_run`, and GitHub only uses the copy
  of `deploy.yml` on `main`. A change to that file only takes effect
  once it's on `main`, even for staging and production runs.
- Setting `autoDeployTrigger: checksPass` on the services would make
  Render wait for green GitHub checks before deploying. It isn't
  enabled yet.

### Caveats

- **Dev staging and dev `main` share a database.** Anything done on
  the staging service shows up on the dev leaderboard. Production is
  not affected.
- **Smoke-test data in production.** Each `verify-production-deploy`
  run writes a `ci-smoke-*` user and score into the production
  database, so they appear on the production leaderboard.
- **Free plans.** Web services spin down when idle, so the first request
  after a while is slow. Free databases expire after a limited period.
  Switch the `plan` fields in `render.production.yaml` to paid plans
  before relying on production for anything long-lived.
- **`/leaderboard` on a hard refresh** returns the API's JSON instead of
  the page, because the frontend route and the API endpoint share a
  path. See the README's *Known limitation* section.

## Rolling back

In the Render dashboard, open the service → **Deploys** → the last good
deploy → **Rollback**. This reuses the old build, so there's no rebuild.
Rolling back **turns off auto-deploy** for that service. Turn it back on
once the fix has gone through dev.
