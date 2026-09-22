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

The `Dockerfile` builds the frontend with Node, then copies the built
static files into a Python image that runs the backend — the backend
serves both the API and the frontend from a single container/port.

Build:

```bash
docker build -t snake-arena .
```

Run, mounting a named volume for the SQLite file so accounts/leaderboard
data survive across container restarts instead of resetting every time
(into its own subdirectory, not `/app` itself, which would shadow the app
code):

```bash
docker run --rm -p 8000:8000 -v snake-arena-db:/app/data -e DATABASE_URL=sqlite:////app/data/snake_arena.db snake-arena
```

Then open http://localhost:8000. The `snake-arena-db` volume is created
automatically on first run and reused (with all prior data) on every run
after that — `docker volume rm snake-arena-db` if you ever want a clean
slate.

If you instead want a throwaway database that resets every run (e.g. for
a quick one-off demo), drop the volume and `DATABASE_URL` override:

```bash
docker run --rm -p 8000:8000 snake-arena
```

To point at a different database instead — Postgres is supported out of
the box (the `psycopg` driver is bundled) — set `DATABASE_URL`:

```bash
docker run --rm -p 8000:8000 -e DATABASE_URL=postgresql+psycopg://user:pass@host/db snake-arena
```

### Running with Postgres via Docker Compose

`docker-compose.yml` runs the app alongside a Postgres container, wired
together and with data persisted in a named volume by default:

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
