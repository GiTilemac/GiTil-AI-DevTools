# Snake Arena

An interactive Snake game with two play modes, plus interactive mockups for
where the multiplayer features are headed: login/signup, a leaderboard, and
watching another player currently in a game.

This is a **frontend-only** project — there is no real backend yet. All data
(users, scores, the live "watch" opponent) is mocked in-memory, routed
through a single facade at `src/api/backendClient.ts` so a real backend can
be swapped in later without touching any page or component.

See [`_docs/plan.md`](_docs/plan.md) for the full project specification
(requirements, architecture, and testing approach).

## Getting started

```bash
npm install
npm run dev
```

Then open the printed local URL (typically http://localhost:5173).

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start the Vite dev server |
| `npm run build` | Type-check and build for production |
| `npm run preview` | Preview the production build locally |
| `npm run test` | Run tests in watch mode |
| `npm run test:run` | Run the full test suite once |
| `npm run typecheck` | Type-check without emitting |

## Using the app

- **Play** (`/play`) — pick a mode, then move with the arrow keys or WASD.
  - *Pass-through*: the snake wraps around the board edges.
  - *Walls*: hitting the boundary ends the game.
  - Finishing a game while logged in submits your score to the leaderboard;
    as a guest you'll be prompted to log in or sign up instead.
- **Login / Signup** (`/login`, `/signup`) — fully interactive, but session
  state is in-memory only and resets on page reload.
- **Leaderboard** (`/leaderboard`) — global high scores, seeded with mock
  players; your own submitted scores appear here too.
- **Watch** (`/watch`) — spectate an always-on simulated bot player, standing
  in for a real opponent until multiplayer exists.

## Project layout

```
src/
  api/         mock backend facade + in-memory "database"
  game/        pure Snake engine + bot simulation (no React, fully testable)
  context/     AuthContext (session state)
  hooks/       useLeaderboard, useLiveGame, useGameLoop
  components/  shared UI (Navbar, GameBoard, ModeSelector, ...)
  pages/       one file per route
  test/        Vitest setup + render helpers
```

## Testing

```bash
npm run test:run
```

Unit tests cover the game engine, bot simulation, and mock backend facade;
component tests cover every interactive page and the auth/leaderboard hooks.
