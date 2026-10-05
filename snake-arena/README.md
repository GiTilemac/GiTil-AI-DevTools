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
that runs two image-backed web services sharing one managed Postgres
database (`snake-arena-db`). Neither builds anything; both pull the
image CI pushed to GitHub Container Registry
(`ghcr.io/gitilemac/snake-arena`):

- **dev** (`snake-arena`) gets every image CI builds from `main`.
- **production** (`snake-arena-prod`) gets the image dev is running,
  when someone runs the **Promote to production** workflow.

**Dev and production are not data-isolated.** Render's free tier
allows only one active database, so anything dev writes (including CI's
`ci-smoke-*` test users and scores) shows up on the production
leaderboard. Setup steps (deploy hook secrets, package visibility,
service URLs in the workflows) are in `_docs/deployment.md`; the
release flow is in `_docs/release-process.md`.

The free plans in `render.yaml` are dev-only (Render expires free
databases after a limited period, and free web services spin down when
idle). Switch the `plan` fields to paid plans for anything long-lived.
Tables are created automatically on first boot.

### CI/CD

Three workflows in `.github/workflows/`:

- **CI** (`ci.yml`) runs backend and frontend tests in parallel, then
  boots the real `docker-compose.yml` stack (app + Postgres) and runs
  `integration-tests/` against it over HTTP. On pushes to `main` it
  then **builds** the image once, tags it `YYYYMMDD-HHMMSS-shortsha`
  (e.g. `20260818-163457-83242da`), pushes it to GHCR, and **deploys**
  it to dev.
- **Deploy** (`deploy.yml`) is called by the other two. It triggers the
  service's Render deploy hook with the exact image tag, waits for
  `/health` to report that tag, and runs the smoke suite against the
  live service.
- **Promote to production** (`promote.yml`) is run by hand. It reads
  the tag dev is running and deploys that same image to production.

Each smoke run writes a uniquely-named `ci-smoke-*` user and score into
the shared leaderboard.

### Rolling back a bad deploy

Every deployed image stays in the registry, so rolling back means
deploying an older tag: use **Rollback** on a previous deploy in the
Render dashboard, or call the service's deploy hook with an older
`imgURL`. See *Rolling back* in `_docs/deployment.md`.

Database schema changes are safe to roll back past: tables are created
via `Base.metadata.create_all()` (backend/app/store.py), which only
ever adds tables, never drops them, so an older image keeps working
against a newer database — it just ignores any columns it doesn't know
about.
