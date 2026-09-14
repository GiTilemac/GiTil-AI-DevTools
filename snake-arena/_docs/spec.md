# Snake Arena — Product & Technical Specification

Status: implemented (frontend-only, mocked backend). See [`plan.md`](plan.md)
for how this was scoped and decided; this document is the reference spec for
what the product does and how it's built.

All application code lives under `frontend/`; every path referenced below
(`src/...`) is relative to that directory.

---

## 1. Overview

Snake Arena is a browser-based Snake game built as the foundation for a
future multiplayer product. Today it's a single-player game client with
interactive mockups of the multiplayer surface — accounts, a leaderboard, and
spectating — so the product experience can be evaluated end-to-end before any
real backend or second player exists.

---

## 2. Product Specification

### 2.1 Goals

- Let a visitor play Snake in the browser in two rule variants.
- Demonstrate the intended multiplayer product shape: sign up, appear on a
  leaderboard, watch someone else play.
- Make every one of those surfaces genuinely interactive (not static
  mockups), so the product can be demoed and user-tested as if the backend
  existed.

### 2.2 Non-goals (current phase)

- Real multiplayer (a second human player, real-time sync between clients).
- Account persistence across sessions/devices.
- Anti-cheat, rate limiting, or any server-side validation (there is no
  server).
- Mobile/touch controls (keyboard only).

### 2.3 Users

A single user role: **player**. A player may be a guest (unauthenticated,
can play but not appear on the leaderboard) or a signed-up user
(authenticated for the lifetime of the browser tab).

### 2.4 Features

#### F1 — Play
A player picks a game mode and plays Snake with keyboard controls.

- **Pass-through mode**: the snake exits one edge of the board and reappears
  on the opposite edge. The only way to lose is self-collision.
- **Walls mode**: the board edges are solid. Touching one ends the game, in
  addition to self-collision.
- Score increases by a fixed amount per food item eaten; the snake grows by
  one segment per food item.
- Mode can be changed only when a game is not actively running (before the
  first move, or after game-over), so a mode swap can't happen mid-run.
- On game-over:
  - Signed-in player: score is submitted to the leaderboard automatically,
    and the UI confirms this.
  - Guest: the UI shows the final score and prompts the player to log in or
    sign up, with links to both — the score is *not* submitted.
- "Play again" resets the board (same mode) without leaving the page.

#### F2 — Accounts (sign up / log in / log out)
- Sign up with a username + password creates an account and immediately
  signs the player in.
- A duplicate username (case-insensitive) is rejected with an inline error.
- Log in validates username + password; wrong credentials show an inline
  error without revealing which field was wrong.
- Once signed in, the player's username is visible everywhere (nav bar) and
  a Logout control appears.
- Accounts and sessions do **not** persist across a page reload — this is a
  deliberate simplification while there's no real backend (see §3.9 for the
  rationale and how this would change with a real backend).

#### F3 — Leaderboard
- Shows all-time high scores, ranked descending, with player name, score,
  and the mode the score was achieved in.
- Seeded with a fixed set of mock players so the board isn't empty on first
  load.
- The signed-in player's own row (if present) is visually highlighted.
- Updates live within the session as games are finished and submitted.

#### F4 — Watch
- Shows a single, always-on simulated opponent ("SnakeBot") playing live,
  standing in for "watch another real player currently in a game" until real
  multiplayer exists.
- The board updates continuously; when the bot dies, a brief pause is shown
  and then a new bot game starts automatically, so there's always something
  to watch.
- Read-only — the viewer cannot control the bot.

### 2.5 Cross-cutting UX requirements

- Every screen is reachable from a persistent navigation bar (Play,
  Leaderboard, Watch, plus Login/Signup or username+Logout depending on auth
  state).
- Loading and error states are shown inline, not via alerts/blocking dialogs
  (e.g. "Logging in…", "Username is already taken.").
- The app is a single-page app: navigating between screens does not reload
  the page.

---

## 3. Technical Specification

### 3.1 Stack

React 18 + TypeScript, built with Vite. Routing via `react-router-dom`
(client-side, `BrowserRouter`). Styling via plain CSS + CSS Modules — no CSS
framework. State via React Context + hooks — no external state library.
Tests via Vitest + React Testing Library (jsdom).

### 3.2 Architecture

```
UI (pages/components)
   -> hooks (useLeaderboard, useLiveGame, useGameLoop)
   -> AuthContext (session state)
   -> backendClient   <-- the ONLY module that knows data is mocked
        -> mockDb (in-memory store)
        -> game/bot.ts (drives the Watch feed)
   -> game/engine.ts  <-- pure rules, used by both the player's game and the bot
```

The `game/` module has no dependency on React, `api/`, or the DOM — it's a
pure state-transition library, which is what makes it exhaustively unit
testable and reusable for both the interactive game and the bot.

The `api/backendClient.ts` facade is the single seam for a future real
backend: every read/write of "server" state — auth, leaderboard, live game
feed — goes through it, and nothing else imports `mockDb` or bot internals
directly. Replacing the mock implementation with real HTTP/WebSocket calls
should require changes only inside `src/api/`.

### 3.3 Data model

```ts
type Direction = 'UP' | 'DOWN' | 'LEFT' | 'RIGHT';
type GameMode = 'pass-through' | 'walls';
type GameStatus = 'idle' | 'running' | 'game-over';

interface Point { x: number; y: number }

interface GameState {
  board: { width: number; height: number };
  mode: GameMode;
  snake: Point[];              // snake[0] is the head
  direction: Direction;
  pendingDirection: Direction | null;
  food: Point;
  score: number;
  status: GameStatus;
  tickCount: number;
}

interface User {
  id: string;
  username: string;
}

interface LeaderboardEntry {
  id: string;
  username: string;
  score: number;
  mode: GameMode;
  achievedAt: string;          // ISO 8601
}
```

Board size: 20×20. Tick interval: 150ms. Score per food: 10 points. Initial
snake length: 3 segments, centered, facing right.

### 3.4 Backend facade contract — `src/api/backendClient.ts`

This is the contract a real backend would need to satisfy to drop in as a
replacement.

```ts
auth.signup(input: { username: string; password: string }): Promise<User>
  // rejects BackendError('USERNAME_TAKEN') on a case-insensitive duplicate

auth.login(input: { username: string; password: string }): Promise<User>
  // rejects BackendError('INVALID_CREDENTIALS') on any mismatch

auth.logout(): Promise<void>

auth.getCurrentUser(): Promise<User | null>

leaderboard.getLeaderboard(): Promise<LeaderboardEntry[]>
  // returns all entries, sorted by score descending

leaderboard.submitScore(input: {
  username: string; score: number; mode: GameMode;
}): Promise<LeaderboardEntry[]>
  // appends an entry and returns the re-sorted board

watch.subscribe(
  onUpdate: (state: GameState) => void,
  intervalMs?: number,
): () => void
  // fires onUpdate immediately with the current state, then on every tick;
  // returns an unsubscribe function
```

Current implementation: `mockDb.ts` holds an in-memory `{ users, leaderboard,
currentUserId }` object; `latency.ts` wraps every return value in a Promise
with simulated network delay (skipped when `import.meta.env.MODE ===
'test'`). No data survives a page reload.

### 3.5 Game engine rules

Implemented in `src/game/engine.ts`, driven by two pure functions:

- `setDirection(state, dir)` — buffers a direction for the next tick. A
  180° reversal (e.g. `LEFT` while moving `RIGHT`) is ignored once the snake
  has more than one segment, since that would be an instant, unavoidable
  self-collision. No-op once the game is over.
- `step(state, rng)` — advances the game by one tick:
  1. Resolve the buffered direction (or keep the current one).
  2. Compute the new head position.
     - *walls mode*: a move that exits the board kills the snake
       (`status -> 'game-over'`), and the snake array is left unchanged so
       the final board freezes at the last valid position.
     - *pass-through mode*: a move that exits the board wraps to the
       opposite edge instead.
  3. Check self-collision against the body (excluding the tail segment,
     since the tail vacates its cell on a non-growing move).
  4. If the new head is on the food cell: grow (keep the tail segment
     instead of dropping it), add 10 to the score, and place new food on a
     random free cell via the injected RNG.
  5. Otherwise: move normally (drop the tail).
- `step` is a no-op once `status === 'game-over'`, so extra ticks after death
  are harmless.

Food placement (`food.ts`) rejection-samples random free cells first, falling
back to scanning all free cells if the board is nearly full, so it never
throws unless the board is completely occupied.

RNG (`rng.ts`) is a seeded mulberry32 PRNG passed explicitly into every
function that needs randomness — nothing calls `Math.random()` directly —
which is what makes food placement and bot behavior deterministic and
reproducible in tests.

### 3.6 Bot ("Watch") behavior

Implemented in `src/game/bot.ts`, reusing `engine.ts`'s `step`/`setDirection`
rather than duplicating movement logic.

- `decideDirection(state)`: greedily picks, among the directions that don't
  reverse into the snake's neck, the one that most reduces Manhattan
  distance to the food while not immediately colliding with itself or (in
  walls mode) the boundary. Falls back to continuing straight if no
  candidate is safe — the bot is allowed to die.
- `advanceBotGame(game)`: one tick of the bot's game. On death, counts down
  `BOT_RESTART_DELAY_TICKS` (10 ticks, ~1.5s) before starting a fresh game on
  the same RNG stream, so the Watch screen always has a live board.
- The bot always plays in `pass-through` mode.
- `backendClient.watch.subscribe` owns exactly one bot game and one shared
  `setInterval`, regardless of how many components are watching — multiple
  subscribers share the same tick, and the interval is torn down when the
  last subscriber unsubscribes.

### 3.7 State management

- `AuthContext` (`src/context/AuthContext.tsx`) is the only piece of
  cross-page client state. It holds `user`, `loading`, `error`, and wraps
  `backendClient.auth.*`. It does **not** call `getCurrentUser()` on mount —
  by design, a fresh page load always starts logged out (see §2.4/F2).
- `useLeaderboard()` loads the board on mount and exposes `submitScore`,
  which is a no-op if no user is logged in.
- `useLiveGame()` subscribes to `backendClient.watch` for the lifetime of the
  component.
- `useGameLoop(mode)` is the only hook that owns a `setInterval` for
  gameplay; it also owns the keyboard event listener (arrow keys and WASD)
  and exposes `changeDirection`, `setMode`, and `restart`.

### 3.8 Routing

`BrowserRouter` with these routes, all rendered inside a persistent
`Navbar`:

| Path | Page | Auth required |
|---|---|---|
| `/` | redirects to `/play` | no |
| `/play` | `PlayPage` | no (score submission requires login) |
| `/login` | `LoginPage` | no |
| `/signup` | `SignupPage` | no |
| `/leaderboard` | `LeaderboardPage` | no |
| `/watch` | `WatchPage` | no |
| `*` | `NotFoundPage` | no |

### 3.9 Known simplifications and their rationale

- **No persistence across reload** (accounts, sessions, submitted scores
  beyond the in-memory DB): there is no real backend, and adding
  `localStorage` would create a false impression of durability that a real
  backend integration would then have to unwind. When a real backend lands,
  `AuthContext` gains a `getCurrentUser()` call on mount (session cookie/JWT
  based), and `backendClient` swaps its mock implementation for real HTTP
  calls without changing its public shape.
- **Single bot instead of a lobby of spectatable players**: there's only one
  simulated opponent because there's no second real player yet. The
  `watch.subscribe` contract (subscribe to a named/identified game, get
  state ticks) is already shaped so a future lobby of real players' game
  feeds could reuse the same pattern per-player.
- **No server-side validation**: score submission trusts the client. A real
  backend must validate that a submitted score is achievable (e.g. recompute
  or bound-check server-side) before accepting it.

### 3.10 Testing strategy

Vitest + React Testing Library, `npm run test:run` (66 tests at time of
writing). Layered:

1. **Pure logic** — `game/engine`, `game/bot`, `game/rng`, `game/food`,
   `api/backendClient`: exhaustive unit tests with no React or DOM involved,
   using the seeded RNG for determinism.
2. **State layer** — `context/AuthContext`, `hooks/useLeaderboard`,
   `hooks/useLiveGame`: tested via `renderHook`, asserting on state
   transitions and error branches.
3. **UI** — every page and the `Navbar`: tested via
   `@testing-library/react`, driving real user interactions (typing, clicks,
   key presses) and asserting on rendered output, including both branches of
   the game-over flow (logged in vs. guest) and fake-timer-driven live
   updates for the Watch screen.

`npm run typecheck` (TypeScript strict mode) and `npm run build` are treated
as part of the definition of done alongside the test suite.

---

## 4. Future work (not in current scope)

- Real backend (persistence, real auth, WebSocket-based live game feed).
- Real multiplayer: a lobby listing actual concurrent players, selectable
  spectating.
- Server-side score validation / anti-cheat.
- Persistent sessions across reloads and devices.
- Mobile/touch controls.
