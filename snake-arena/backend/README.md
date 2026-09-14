# Snake Arena backend

FastAPI implementation of the contract in `../openapi.yaml`.

## Commands (run from inside `backend/`)

- `uv sync` — install dependencies (first time / after changing them)
- `uv run uvicorn app.main:app --reload` — start the dev server on `:8000`
- `uv run pytest` — run the test suite

## Structure

- `app/models.py` — Pydantic request/response schemas
- `app/store.py` — in-memory data store, seeded on import
- `app/auth.py` — password hashing and bearer-token session handling
- `app/routers/` — one module per resource (`auth`, `leaderboard`, `watch`)
- `app/main.py` — app wiring
