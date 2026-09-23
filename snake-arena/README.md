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
that provisions this same Docker image as a web service plus a managed
Postgres database, wired together via `DATABASE_URL`:

1. Push this repo to GitHub (already done if you're reading this from
   the remote).
2. In the Render dashboard: **New > Blueprint**, pick this repo, and
   Render will pick up `render.yaml` from the repo root automatically.
3. Click **Apply**. Render builds `snake-arena/Dockerfile`, creates the
   `snake-arena-db` Postgres instance, and sets `DATABASE_URL` on the web
   service to that database's connection string.

The free Postgres plan in `render.yaml` is dev-only (Render expires free
databases after a limited period) — switch `databases[0].plan` to a paid
plan for anything long-lived. No other setup is required: tables are
created automatically on first boot, and the backend serves both the API
and the built frontend from the one service, same as the Docker Compose
setup above.
