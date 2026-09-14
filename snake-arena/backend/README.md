# Snake Arena backend

FastAPI implementation of the contract in `../openapi.yaml`.

## Commands (run from inside `backend/`)

- `uv sync` — install dependencies (first time / after changing them)
- `uv run uvicorn app.main:app --reload` — start the dev server on `:8000`
- `uv run pytest` — run the test suite

## Database

Users, tokens, and the leaderboard are stored via SQLAlchemy, configured
by the `DATABASE_URL` environment variable:

- Default: `sqlite:///./snake_arena.db` (a local file, created on first run)
- Tests always use an isolated in-memory SQLite DB (`sqlite://`), set in
  `tests/conftest.py`, regardless of `DATABASE_URL` in your shell.

No SQLite-specific SQL or syntax is used anywhere in the app, so pointing
`DATABASE_URL` at another backend is meant to be the only change needed
to move databases — e.g. Postgres later via `postgresql+psycopg://...`
once a Postgres driver (`uv add psycopg[binary]`) is added.

The bot/watch simulation behind `/watch/live` is unrelated ephemeral
runtime state (not user data) and always stays in-memory, regardless of
`DATABASE_URL`.

## Structure

- `app/models.py` — Pydantic request/response schemas
- `app/db.py` — SQLAlchemy engine/session setup (reads `DATABASE_URL`)
- `app/db_models.py` — SQLAlchemy ORM models (users, tokens, leaderboard)
- `app/store.py` — data access layer on top of the ORM models, plus the
  in-memory bot/watch state
- `app/auth.py` — password hashing and bearer-token session handling
- `app/routers/` — one module per resource (`auth`, `leaderboard`, `watch`)
- `app/main.py` — app wiring
