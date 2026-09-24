# Testing Snake Arena

Snake Arena has three test suites. Each one covers a different layer, and
CI runs all three on every push and PR to `main`/`staging`.

| Suite            | Location              | Runs against                                  | Tool                  |
|------------------|-----------------------|-----------------------------------------------|-----------------------|
| Backend unit     | `backend/tests/`      | FastAPI app in-process, in-memory SQLite      | pytest + `TestClient` |
| Frontend unit    | `frontend/src/**/*.test.ts(x)` | Components and game logic in jsdom   | Vitest + Testing Library |
| Integration/e2e  | `integration-tests/`  | A running stack over real HTTP (`BASE_URL`)   | pytest + httpx        |

## Backend unit tests

```bash
cd backend
uv run pytest          # or: make test
```

- `tests/conftest.py` sets `DATABASE_URL=sqlite://` (in-memory) before
  the app is imported, so the tests are fast and leave no file on disk.
- The autouse `fresh_store` fixture resets the store before every test,
  so users, tokens and scores can't leak from one test into another.
- You can run the same suite against Postgres by setting `DATABASE_URL`
  yourself. The conftest only sets it if it isn't already set:

  ```bash
  DATABASE_URL=postgresql+psycopg://snake:snake@localhost:5432/snake_arena uv run pytest
  ```

  This needs a Postgres you can reach from your machine. The Compose
  `db` service doesn't publish its port by default.

The files are split by feature: `test_auth.py`, `test_game.py`,
`test_leaderboard.py`, `test_watch.py`, `test_bot.py`, `test_store.py`
and `test_db.py`.

## Frontend unit tests

```bash
cd frontend
npm run typecheck      # tsc --noEmit
npm run test:run       # single Vitest run (what CI uses)
npm test               # Vitest in watch mode, for local development
```

Test files live next to the code they cover, for example
`src/game/engine.test.ts` and `src/pages/LoginPage.test.tsx`. Game logic
(`src/game/`) is tested as plain functions. Pages and contexts are
rendered with Testing Library. `src/api/backendClient.test.ts` covers
the HTTP facade.

CI treats a type error as a failure, so run `typecheck` before pushing.

## Integration / e2e tests

`integration-tests/test_smoke.py` is a black-box smoke suite. It only
talks to the app over HTTP, which makes it the only suite that checks
the real Postgres database, the Docker image, and the serving of the
built frontend. It covers:

- `GET /health`
- the frontend being served on `/` (SPA fallback)
- signing up, submitting a score, and seeing it on the leaderboard

Against the local Docker Compose stack:

```bash
docker compose up --build -d      # from snake-arena/
cd backend
uv run pytest ../integration-tests -v
docker compose down -v            # -v also deletes the test data
```

Against any other deploy, set `BASE_URL`. It defaults to
`http://localhost:8000`.

```bash
BASE_URL=https://<service>.onrender.com uv run pytest ../integration-tests -v
```

Each run creates a user named `ci-smoke-<random>` with a score. On
Render that data lands in the shared staging/production database (see
[deployment.md](deployment.md)), so it shows up on the live leaderboard.

## In CI

There are two workflows in `.github/workflows/`.

`ci.yml` (**CI**) runs on every push and PR to `main`/`staging`:

1. `backend-tests` and `frontend-tests` run in parallel.
2. `integration-e2e` runs only if both pass. It boots `docker-compose.yml`,
   waits for `/health`, runs the smoke suite, prints `docker compose logs`
   if anything fails, and always tears the stack down.

`deploy.yml` (**Deploy**) starts when a CI run finishes. If CI passed
for a push to `staging` or `main`, it runs `verify-staging-deploy` or
`verify-production-deploy`, which runs the same smoke suite against the
live Render deploy.

If a CI job fails, the jobs after it are skipped and Deploy doesn't
verify anything. This does
**not** stop Render from deploying. See
[release-process.md](release-process.md).

## Adding tests

- Backend behavior (endpoints, validation, persistence): add to the
  matching `backend/tests/test_*.py` and use the `client`,
  `signed_up_user` and `auth_headers` fixtures.
- Frontend logic or UI: add a `*.test.ts(x)` file next to the module.
- Anything that depends on the real image, Postgres, or static serving:
  add a test to `integration-tests/`. It has to work against a stack
  that already has data in it, which is why tests use unique usernames
  instead of relying on a clean database.
