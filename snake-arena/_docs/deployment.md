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

`render.yaml`, at the repo root, is a Render Blueprint defining both
environments:

| Environment | Service            | Branch       | Database         |
|-------------|--------------------|--------------|------------------|
| Dev         | `snake-arena`      | `main`       | `snake-arena-db` |
| Production  | `snake-arena-prod` | `production` | `snake-arena-db` |

Both services build `snake-arena/Dockerfile`, use `/health` as their
health check, and run on the free plan. They **share one Postgres
database**, because Render's free tier allows only one active database
(a second one is rejected with "cannot have more than one active tier
database"). See *Caveats* below for what that means.

`/health` also returns the deployed commit (`{"status": "ok",
"commit": "<sha>"}`), taken from the `RENDER_GIT_COMMIT` variable Render
sets on each deploy. The workflows use it to tell when a new deploy is
live. Outside Render, `commit` is `null`.

The dev service keeps its original name because Render identifies
Blueprint services by name. Renaming it would create a new service and
leave the old one behind.

### First-time setup

`render.yaml` is already applied as a Blueprint. To add production:

1. Create the `production` branch **before** merging the change that
   adds `snake-arena-prod`, so the new service has a branch to deploy:

   ```bash
   git fetch origin
   git push origin origin/main:refs/heads/production
   ```

2. Merge the change to `main`. Render syncs the Blueprint and creates
   `snake-arena-prod`. If it doesn't, open the Blueprint in the Render
   dashboard and click **Manual Sync**.
3. `render.yaml` used to define a `snake-arena-staging` service.
   Removing a service from a Blueprint doesn't delete it, so delete it
   in the Render dashboard (service → **Settings** → **Delete Web
   Service**). Delete the `staging` branch once nothing on it is
   missing from `main`.
4. In GitHub, go to **Settings → Secrets and variables → Actions →
   Variables** and set:

   | Variable          | Value                          |
   |-------------------|--------------------------------|
   | `RENDER_URL_DEV`  | `snake-arena` service URL      |
   | `RENDER_URL_PROD` | `snake-arena-prod` service URL |

   Delete `RENDER_URL_STAGING` and `RENDER_URL_PRODUCTION`; nothing
   reads them any more.
5. Go to **Settings → Environments**, create an environment named
   `production`, and add required reviewers so that every promotion
   needs an approval.
6. If `production` has branch protection, make sure the Promote
   workflow can still push to it, or it will fail at the push.
7. Once **Verify dev deploy** passes for the merge, run **Promote to
   production** to bring production up to date.

### How deploys happen

- **Dev:** Render **auto-deploys every push** to `main`. The CI
  workflow doesn't start or gate the deploy, because Render only
  supports a static API key or deploy hook, not GitHub OIDC. Once
  **CI** (`.github/workflows/ci.yml`) passes for the push, **Deploy**
  (`.github/workflows/deploy.yml`) waits up to 15 minutes for dev's
  `/health` to report that commit, then runs `integration-tests/`
  against it. A broken deploy shows up as a failed run.
- **Production:** only the manually-run **Promote to production**
  workflow (`.github/workflows/promote.yml`) deploys it. It finds the
  commit dev is running, checks that the commit is on `main` and passed
  CI, smoke-tests dev, and waits for approval. Then it fast-forwards
  `production` to that commit. Render deploys it, and the workflow
  waits for production's `/health` to report the commit and runs
  `integration-tests/` against production.
- Production is verified inside Promote, not Deploy, because pushes
  made with `GITHUB_TOKEN` don't trigger other workflows.
- `GITHUB_TOKEN` also can't push a ref update that changes files under
  `.github/workflows/`. If a promotion includes such a change, its push
  is rejected. Add a `PROMOTE_TOKEN` repository secret (a fine-grained
  token with Contents and Workflows write on this repo) and Promote
  uses it instead.
- Deploy is triggered by `workflow_run`, and GitHub only uses the copy
  of `deploy.yml` on `main`.

### Caveats

- **Shared database.** Dev and production read and write the same
  data. Users and scores created in dev, and the `ci-smoke-*` user and
  score every Deploy and Promote smoke run writes, appear on the
  production leaderboard. A bug in a dev deploy can damage production
  data. To separate them, add a second database on a paid plan (or use
  a separate Render account) and point `snake-arena-prod` at it.
- **Free plans.** Web services spin down when idle, so the first request
  after a while is slow. Free databases expire after a limited period.
- **`/leaderboard` on a hard refresh** returns the API's JSON instead of
  the page, because the frontend route and the API endpoint share a
  path. See the README's *Known limitation* section.

## Rolling back

In the Render dashboard, open the service → **Deploys** → the last good
deploy → **Rollback**. This reuses the old build, so there's no rebuild.
Rolling back **turns off auto-deploy** for that service. Turn it back on
once the fix has gone through dev.

After rolling back production, the `production` branch still points at
the bad commit. That's fine: the next promotion fast-forwards past it,
so a fix only has to land on `main` and pass dev. Turn auto-deploy back
on for `snake-arena-prod` **before** running Promote, or Render won't
deploy the push and Promote times out waiting for it.
