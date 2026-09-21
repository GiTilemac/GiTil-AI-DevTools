## Snake Arena

The frontend lives in `frontend/` (React + TypeScript + Vite) and talks to
the real backend in `backend/` (FastAPI + SQLAlchemy/SQLite) over
HTTP/SSE, via the single facade at `frontend/src/api/backendClient.ts` —
never bypass it. The backend implements the contract in `openapi.yaml`.
Full spec: `_docs/plan.md` and `_docs/spec.md`; current project state and
recent history: `_docs/context-summary.md` (keep that one updated as
things change — the spec docs are not).

Commands (run from inside `frontend/`): `npm run dev`, `npm run test:run`,
`npm run typecheck`, `npm run build`.

Commands (run from inside `backend/`): `uv sync`, `uv run uvicorn app.main:app --reload`,
`uv run pytest`. Use uv for its dependency management (`uv add`, `uv run python`).

Regularly commit code to git.
