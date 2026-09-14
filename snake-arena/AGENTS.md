## Snake Arena

The frontend lives in `frontend/` (React + TypeScript + Vite) and still
talks to a mocked backend via the single facade at
`frontend/src/api/backendClient.ts` — never bypass it. A real backend now
exists in `backend/` (FastAPI) implementing the contract in
`openapi.yaml`, but the frontend has not been wired up to it yet; wiring
that up means reimplementing `backendClient.ts` against real HTTP calls
without changing its public shape. Full spec: `_docs/plan.md` and
`_docs/spec.md`.

Commands (run from inside `frontend/`): `npm run dev`, `npm run test:run`,
`npm run typecheck`, `npm run build`.

Commands (run from inside `backend/`): `uv sync`, `uv run uvicorn app.main:app --reload`,
`uv run pytest`. Use uv for its dependency management (`uv add`, `uv run python`).

Regularly commit code to git.
