## Snake Arena

Frontend-only (React + TypeScript + Vite). There is no real backend yet —
all data is mocked. Every "backend" call goes through the single facade at
`src/api/backendClient.ts`; never bypass it. Full spec: `_docs/plan.md`.

Commands: `npm run dev`, `npm run test:run`, `npm run typecheck`, `npm run build`.

If/when a real backend is added, use uv for its dependency management
(`uv sync`, `uv add`, `uv run python`).

Regularly commit code to git.
