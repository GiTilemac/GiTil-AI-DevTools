# Snake Arena — Project Specification

> **Status note:** this document records how the project was originally
> scoped, as a *client-only, mocked-backend* app. A real backend (FastAPI +
> SQLAlchemy/SQLite) has since been built and wired up — see
> `context-summary.md` for current state and `../AGENTS.md` for pointers.
> The scoping decisions and frontend architecture below are still accurate;
> statements about there being no real backend / everything being mocked
> are not.

## Goal

An interactive Snake game web app that doubles as a foundation for future
multiplayer features. Two playable game modes, plus the multiplayer
experience: authentication, a leaderboard, and spectating ("watching")
another player currently in a game. Started as a client-only build with
everything mocked behind a single facade, specifically so a real backend
could be swapped in later without touching pages, components, or hooks —
that swap has since happened (see status note above).

All application code lives under `frontend/` (a plain React + TypeScript +
Vite project); paths below (`src/...`) are relative to that directory. Run
all commands (`npm install`, `npm run dev`, `npm run test:run`, etc.) from
inside `frontend/`.

## Requirements (as given)

- Build the Snake game with two modes: pass-through and walls.
- Prepare for multiplayer: a leaderboard, and watching other players currently
  playing.
- Add interactive mockups for login/signup and for watching other players.
- Everything must be interactive: log in, sign up, see your username once
  logged in, see the leaderboard, watch someone else play (implemented as a
  simulated bot, since there's no real backend to supply a second human).
- Do not implement a real backend — mock everything — but centralize all
  "backend" calls in one place.
- Cover all logic with tests.

## Decisions made during scoping

These were resolved via clarifying questions before implementation began:

| Area | Decision |
|---|---|
| Frontend stack | React + TypeScript + Vite |
| Routing | React Router, multi-route SPA (`/play`, `/login`, `/signup`, `/leaderboard`, `/watch`) |
| Styling | Plain CSS + CSS Modules (no Tailwind) |
| Package manager | npm |
| Game modes | **pass-through**: snake wraps around the board edges. **walls**: hitting the boundary ends the game. |
| Auth persistence | In-memory only — no `localStorage`. Session state resets on page reload. |
| Leaderboard | Global high scores, seeded with mock players; the logged-in user's finished games submit their score and the board re-sorts. |
| Watch screen | A single always-on deterministic bot game (no lobby/selection UI) driven by a greedy-toward-food algorithm. |
| Test tooling | Vitest + React Testing Library (jsdom) |

## Architecture

### Centralized backend facade — `src/api/backendClient.ts`

The single point of contact for anything that would talk to a real backend.
Nothing else in the app touches mock data directly.

```
backendClient.auth.signup(input)        -> Promise<User>
backendClient.auth.login(input)         -> Promise<User>
backendClient.auth.logout()             -> Promise<void>
backendClient.auth.getCurrentUser()     -> Promise<User | null>
backendClient.leaderboard.getLeaderboard()   -> Promise<LeaderboardEntry[]>
backendClient.leaderboard.submitScore(input) -> Promise<LeaderboardEntry[]>
backendClient.watch.subscribe(onUpdate, intervalMs?) -> unsubscribe fn
```

Originally backed by an in-memory mock (`src/api/mockDb.ts` + simulated
latency); now backed by real `fetch`/`EventSource` calls against the
FastAPI backend in `../backend/` (base URL via `VITE_API_BASE_URL`,
default `127.0.0.1:8000`) — `mockDb.ts` and the latency wrapper were
deleted once the swap happened. Errors are typed (`BackendError` with
`USERNAME_TAKEN` / `INVALID_CREDENTIALS` codes) so the UI has something
concrete to branch on.

`watch.subscribe` owns a single shared bot game and interval; the interval
starts on the first subscriber and stops when the last one unsubscribes, so
the Watch screen and any future "who's live" list can share one feed.

### Pure game engine — `src/game/`

Framework-free reducer logic, fully unit-testable without React or timers:

- `types.ts` / `constants.ts` — `GameState`, `Direction`, `GameMode`, board
  size (20x20), tick interval (150ms), score per food (10).
- `rng.ts` — deterministic seeded PRNG (mulberry32), so food placement and bot
  behavior are reproducible in tests.
- `food.ts` — places food on a free cell using the injected RNG.
- `engine.ts` — `createInitialState`, `setDirection` (buffers input, blocks
  180° reversal), `step` (moves the snake, applies mode-specific boundary
  behavior, detects self-collision, grows on food, is a no-op once
  game-over).
- `bot.ts` — the Watch screen's opponent. `decideDirection` picks the
  non-reversing move that most reduces Manhattan distance to food while
  avoiding immediate death; `advanceBotGame` reuses `engine.step` and
  auto-restarts the bot 10 ticks after it dies, so Watch always has something
  live to show.

### React state

- `context/AuthContext.tsx` — the only piece of client-side "session" state;
  wraps `backendClient.auth`, exposes `user`, `loading`, `error`,
  `login`/`signup`/`logout`.
- `hooks/useLeaderboard.ts` — loads/refreshes leaderboard entries, submits the
  current user's score.
- `hooks/useLiveGame.ts` — subscribes to `backendClient.watch` for the Watch
  screen.
- `hooks/useGameLoop.ts` — drives the interactive Play screen: keyboard input
  (arrows + WASD), the tick interval, mode switching, and restart, all on top
  of the pure `game/engine.ts` reducer.

No Redux/Zustand — Context + hooks only, per the project's "don't add
abstractions beyond what's needed" preference.

### Pages & shared components

- `Navbar` — Play/Leaderboard/Watch links; shows username + Logout when
  signed in, Log in/Sign up when not.
- `GameBoard` — pure renderer of a `GameState`; reused as-is by both the
  interactive Play screen and the read-only Watch screen.
- `ModeSelector`, `ScoreBar`, `LeaderboardTable` — small presentational
  components.
- `PlayPage` — mode selection, live play, game-over panel. Anyone can play;
  a finished game auto-submits to the leaderboard if logged in, otherwise
  prompts to log in/sign up instead of submitting.
- `LoginPage` / `SignupPage` — interactive forms against `AuthContext`,
  inline error states (wrong credentials, duplicate username).
- `LeaderboardPage` — sorted score table, highlights the current user's row.
- `WatchPage` — live-updating board for the always-on demo bot.

## Testing

Vitest + React Testing Library, run via `npm run test:run`. Full coverage
split into:

- **Pure logic** (no React): `rng`, `food`, `engine` (wrap vs. walls death,
  self-collision, growth/scoring, buffered input, no-op after game-over),
  `bot` (never reverses into itself, runs hundreds of ticks without throwing,
  deterministic replay, restart timing), `backendClient` (signup/login error
  cases, leaderboard sort/submit, watch subscribe/unsubscribe).
- **Context/hooks**: `AuthContext`, `useLeaderboard`, `useLiveGame`.
- **Components/pages**: `Navbar`, `LoginPage`, `SignupPage`, `PlayPage`
  (mode switching, keyboard-driven movement, both game-over branches),
  `LeaderboardPage`, `WatchPage`.

66 tests, all passing as of this writing. `npm run typecheck` and
`npm run build` are also clean.

## Explicitly out of scope (for now)

- ~~A real backend / persistence layer~~ — done, see status note at top.
- Auth session persistence across page reloads (still deliberate — the
  bearer token is kept in memory only by design, not because there's no
  backend to persist it against; see `spec.md` §2.4/§3.9).
- A lobby of multiple simultaneously-spectatable players (one always-on bot
  stands in for "watch a live player").
- Any styling framework beyond plain CSS/CSS Modules.
