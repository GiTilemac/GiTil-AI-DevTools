# Deploying Snake Arena

Snake Arena ships as **one Docker image** that serves both the API and
the built frontend on port 8000. The only thing it needs is a database,
set through `DATABASE_URL`. That same image runs locally under Docker
Compose and on Render.

CI builds the image **once** per change, pushes it to GitHub Container
Registry, and Render pulls it. Dev and production run byte-identical
images; production never builds anything.

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
returns `{"status": "ok", "version": "<image tag>"}`. The tag comes from
the `APP_VERSION` build argument, which CI sets. Images built without it
(local builds, Docker Compose) report `"version": null`.

## Configuration

| Variable       | Default                          | Notes                                              |
|----------------|----------------------------------|----------------------------------------------------|
| `DATABASE_URL` | `sqlite:///./snake_arena.db`     | Use `postgresql+psycopg://…` for Postgres. Plain `postgres://` or `postgresql://` URLs, like the ones Render provides, are rewritten to use psycopg automatically. |
| `APP_VERSION`  | unset (`""` in local builds)     | The image tag. Baked in by CI's build job; reported by `/health` and as OpenTelemetry `service.version`. Don't set it by hand. |
| `DEPLOYMENT_ENVIRONMENT` | `local`                | `dev` / `production` on Render (`render.yaml`). OpenTelemetry `deployment.environment.name`. |
| `OTEL_SERVICE_NAME` | `snake-arena`               | OpenTelemetry `service.name`. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | unset             | OTLP/HTTP endpoint for traces and metrics. Unset means nothing is exported. |
| `OTEL_EXPORTER_OTLP_HEADERS` | unset              | Auth headers for the endpoint, e.g. `Authorization=Basic …`. |
| `OTEL_TRACES_EXPORTER` | unset                    | `console` prints spans to stdout, for local debugging. |
| `OTEL_SDK_DISABLED` | unset                       | `true` turns OpenTelemetry off (the test suite does this). |

The schema is created on startup (`Base.metadata.create_all()` in
`backend/app/store.py`). There's no migration step, but existing tables
are never altered either. See *Database changes* in
[release-process.md](release-process.md).

## Telemetry (OpenTelemetry)

`backend/app/telemetry.py` sets up OpenTelemetry at startup:

- **Traces** for every HTTP request (FastAPI instrumentation) and every
  database query (SQLAlchemy instrumentation). `/health` is excluded,
  because Render and the workflows poll it constantly.
- **Metrics** from the same instrumentations (request durations,
  connection pool usage).

Every span and metric carries these resource attributes:

| Attribute                     | Source                     | Example                     |
|-------------------------------|----------------------------|-----------------------------|
| `service.name`                | `OTEL_SERVICE_NAME`        | `snake-arena`               |
| `deployment.environment.name` | `DEPLOYMENT_ENVIRONMENT`   | `production`                |
| `deployment.environment`      | same (older attribute name, still used by many backends) | `production` |
| `service.version`             | `APP_VERSION` (image tag)  | `20261005-120000-abc1234`   |

Data is exported over **OTLP/HTTP** to whatever
`OTEL_EXPORTER_OTLP_ENDPOINT` points at; nothing is exported while it's
unset.

### Backend: Grafana Cloud

Both Render services send straight to Grafana Cloud's OTLP gateway,
`https://otlp-gateway-prod-eu-west-2.grafana.net/otlp` (set in
`render.yaml`). Traces land in Tempo and metrics in Mimir. There's no
self-hosted OpenTelemetry Collector: on Render's free plan it would
spin down when idle and drop data, and nothing here needs one yet
(sampling, filtering, fan-out). Adding one later only changes the
endpoint.

The gateway needs an auth header, which contains the Grafana token, so
it isn't in the repo:

1. In Grafana Cloud, open the stack → **Connections → OpenTelemetry
   (OTLP)** and generate a token. Copy the `OTEL_EXPORTER_OTLP_HEADERS`
   value it shows (`Authorization=Basic%20<base64>`; keep the `%20`).
2. In Render, add it as `OTEL_EXPORTER_OTLP_HEADERS` under
   **Environment** on both `snake-arena` and `snake-arena-prod`.

Without the header, the exporter logs `401` errors and nothing arrives.
In Grafana, **Explore → Tempo** shows traces; filter with
`resource.deployment.environment="production"` (or `"dev"`) and group
by `resource.service.version` to compare releases.

To see spans locally:

```bash
OTEL_TRACES_EXPORTER=console uv run uvicorn app.main:app --reload
```

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

## Registry: GitHub Container Registry

Images live at `ghcr.io/gitilemac/snake-arena`. GHCR was chosen because
workflows push to it with the built-in `GITHUB_TOKEN` (no registry
account or extra secret), it's free for public repositories, and
Render pulls public images from it without credentials.

| Tag                      | Meaning                                         | Moves? |
|--------------------------|-------------------------------------------------|--------|
| `YYYYMMDD-HHMMSS-shortsha` | One build: UTC build time + the 7-character commit SHA, e.g. `20260818-163457-83242da` | No     |
| `dev`                    | The image currently deployed to dev             | Yes    |
| `prod`                   | The image currently deployed to production      | Yes    |

Only the timestamped tags are ever deployed by the workflows. The
`dev`/`prod` tags exist so that a Render Blueprint sync, which deploys
whatever `render.yaml` points at, lands on the image already running.
Render refuses to sync while they don't exist, so CI's build job
creates any that are missing, pointing at the image it just built.

The package must be **public** for Render to pull it without
credentials. Check under the repo's **Packages** → `snake-arena` →
**Package settings** → **Change visibility**. If it has to stay
private, add a GHCR registry credential in Render (a token with
`read:packages`) and reference it with `creds` in `render.yaml`.

## Render

`render.yaml`, at the repo root, is a Render Blueprint defining both
environments as image-backed services:

| Environment | Service            | Image URL in `render.yaml`            | Deployed by      | Database         |
|-------------|--------------------|---------------------------------------|------------------|------------------|
| Dev         | `snake-arena`      | `ghcr.io/gitilemac/snake-arena:dev`   | CI, on `main`    | `snake-arena-db` |
| Production  | `snake-arena-prod` | `ghcr.io/gitilemac/snake-arena:prod`  | Promote, by hand | `snake-arena-db` |

Both use `/health` as their health check and run on the free plan.
They **share one Postgres database**, because Render's free tier allows
only one active database (a second one is rejected with "cannot have
more than one active tier database"). See *Caveats* below.

Service URLs and the image name are written into the workflows
(`DEV_URL`, `PROD_URL`, `IMAGE` in `deploy.yml` and `promote.yml`).
Render appends a random suffix when a name is taken, so copy URLs from
each service's page in the dashboard.

### Pipeline

1. **Test** (`ci.yml`, every PR and push to `main`): backend tests,
   frontend tests, then the Docker Compose integration suite.
2. **Build** (`ci.yml` job `build`, pushes to `main` only, after the
   tests pass): build the image once and push
   `ghcr.io/gitilemac/snake-arena:<YYYYMMDD-HHMMSS-shortsha>`.
3. **Deploy to dev** (`ci.yml` job `deploy-dev`, which runs
   `deploy.yml`): call dev's Render deploy hook with that exact tag,
   wait until dev's `/health` reports it, move the `dev` tag to it, and
   run `integration-tests/` against dev.
4. **Promote to production** (`promote.yml`, run by hand): read the tag
   from dev's `/health`, check the image exists and production isn't
   already on it, summarize the commits that will ship, then run the
   same `deploy.yml` against production (moving the `prod` tag).

`deploy.yml` is the only place that deploys. Each environment's runs
are serialized (`concurrency`), and the job runs in a GitHub environment
named after the target (`dev` or `production`), so required reviewers
on `production` turn every promotion into an approval step.

### First-time setup

Moving from Render building the repo to Render pulling images:

1. **Deploy hooks.** In Render, open each service → **Settings** →
   **Deploy Hook** and copy the URL. In GitHub, go to **Settings →
   Secrets and variables → Actions → Secrets** and add them as
   `RENDER_DEPLOY_HOOK_DEV` (`snake-arena`) and
   `RENDER_DEPLOY_HOOK_PROD` (`snake-arena-prod`). Treat them as
   secrets: anyone with the URL can trigger a deploy.
2. **Merge the change to `main`.** CI tests, builds and pushes the
   first image, then tries to deploy it to dev.
3. **Make the package public** (see *Registry* above).
4. **Switch the services to the image.** Render syncs `render.yaml` on
   merge (or open the Blueprint → **Manual Sync**). The services change
   from building the repo to pulling `:dev` / `:prod`. Render refuses
   the sync ("image … not found") until those tags exist; CI's build
   job creates them, pointing at its image, whenever they're missing.
   So on first setup production also starts on that build, the same
   commit as dev.
   - If Render refuses to change an existing service's runtime, delete
     `snake-arena` and `snake-arena-prod` in the dashboard and sync
     again to recreate them. Their URLs and deploy hooks will change:
     update `DEV_URL`/`PROD_URL` in the workflows and both secrets.
5. **Re-run the `Deploy to dev` job** of that CI run (if it failed
   because the service wasn't switched yet). It deploys the image and
   confirms it with the smoke tests.
6. **Run Promote to production.** Production already runs that image
   after the sync, so Promote reports it's up to date until the next
   change reaches dev.
7. **Clean up.** The `production` branch is no longer used and can be
   deleted, along with any `PROMOTE_TOKEN` secret.

### Caveats

- **Shared database.** Dev and production read and write the same
  data. Users and scores created in dev, and the `ci-smoke-*` user and
  score every deploy's smoke run writes, appear on the production
  leaderboard. A bug in a dev deploy can damage production data. To
  separate them, add a second database on a paid plan (or use a
  separate Render account) and point `snake-arena-prod` at it.
- **Render pulls on every deploy** and doesn't keep old images, so
  deleting an image from GHCR breaks rollbacks to it.
- **Images accumulate** in GHCR, one per push to `main`. Prune old
  timestamped tags from the package page if needed, but keep anything
  you might roll back to.
- **Free plans.** Web services spin down when idle, so the first request
  after a while is slow. Free databases expire after a limited period.
- **`/leaderboard` on a hard refresh** returns the API's JSON instead of
  the page, because the frontend route and the API endpoint share a
  path. See the README's *Known limitation* section.

## Rolling back

Every deployed image is still in the registry, so rolling back means
deploying an older tag:

- **Render dashboard:** open the service → **Events**/**Deploys** → the
  last good deploy → **Rollback**. Render pulls that deploy's image
  again.
- **Deploy hook:** pick a tag from the package page and run
  `curl -X POST "$RENDER_DEPLOY_HOOK_PROD&imgURL=ghcr.io%2Fgitilemac%2Fsnake-arena%3A<tag>"`.

Either way, the `prod` tag still points at the bad image, so a
Blueprint sync would bring it back. The next promotion moves it again.
Ship the fix through dev and promote as usual.
