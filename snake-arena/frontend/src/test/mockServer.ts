/**
 * A fake HTTP + SSE backend for tests, standing in for the real FastAPI
 * server (`snake-arena/backend/`) so `backendClient.ts`'s real
 * fetch/EventSource-based implementation can be exercised without a
 * running server. Installed once via `installMockBackend()` (see
 * `setupTests.ts`) by stubbing `global.fetch` and `global.EventSource`;
 * reset between tests via `resetMockBackend()`.
 *
 * Mirrors the contract in `openapi.yaml`: seeded leaderboard, bearer
 * tokens, and a shared bot game driving `/watch/live` (reusing the real
 * game engine/bot/rng from `src/game`, same as the real backend does).
 */

import { vi } from 'vitest';
import { advanceBotGame, createBotGame, type BotGame } from '../game/bot';
import { TICK_INTERVAL_MS } from '../game/constants';
import type { GameMode, GameState } from '../game/types';
import type { LeaderboardEntry } from '../api/types';

interface MockUser {
  id: string;
  username: string;
  password: string;
}

function nextId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

function seedLeaderboard(): LeaderboardEntry[] {
  const entries: LeaderboardEntry[] = [
    { id: 'seed-1', username: 'PixelViper', score: 480, mode: 'walls', achievedAt: '2026-09-01T10:00:00.000Z' },
    { id: 'seed-2', username: 'GridMaster', score: 410, mode: 'pass-through', achievedAt: '2026-09-02T10:00:00.000Z' },
    { id: 'seed-3', username: 'LoopHound', score: 360, mode: 'pass-through', achievedAt: '2026-09-03T10:00:00.000Z' },
    { id: 'seed-4', username: 'ByteCoil', score: 300, mode: 'walls', achievedAt: '2026-09-04T10:00:00.000Z' },
    { id: 'seed-5', username: 'TailWhip', score: 250, mode: 'walls', achievedAt: '2026-09-05T10:00:00.000Z' },
    { id: 'seed-6', username: 'CrunchApple', score: 180, mode: 'pass-through', achievedAt: '2026-09-06T10:00:00.000Z' },
    { id: 'seed-7', username: 'SlowSlither', score: 90, mode: 'walls', achievedAt: '2026-09-07T10:00:00.000Z' },
  ];
  return entries.sort((a, b) => b.score - a.score);
}

let users: MockUser[] = [];
let leaderboard: LeaderboardEntry[] = seedLeaderboard();
let tokens = new Map<string, string>(); // token -> user id

// -- watch/bot state: one shared game + interval, mirroring the real
// backend's `store.tick_watch` (advance at most once per tick, fan out to
// every open connection) --
let botGame: BotGame | null = null;
let watchInterval: ReturnType<typeof setInterval> | null = null;
const watchListeners = new Set<(state: GameState) => void>();

function tickWatch(): void {
  if (!botGame) return;
  botGame = advanceBotGame(botGame);
  watchListeners.forEach((listener) => listener(botGame!.state));
}

function ensureBotGame(): GameState {
  if (!botGame) {
    botGame = createBotGame();
  }
  if (!watchInterval) {
    watchInterval = setInterval(tickWatch, TICK_INTERVAL_MS);
  }
  return botGame.state;
}

class MockEventSource {
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((event: unknown) => void) | null = null;

  private closed = false;
  private readonly listener = (state: GameState) => {
    this.onmessage?.({ data: JSON.stringify(state) });
  };

  constructor(_url: string) {
    const initial = ensureBotGame();
    watchListeners.add(this.listener);
    // Deferred to a microtask so `onmessage` (assigned synchronously right
    // after `new EventSource(...)`, same as in real code) is already set
    // by the time this fires — real SSE is inherently async the same way.
    Promise.resolve().then(() => {
      if (!this.closed) {
        this.listener(initial);
      }
    });
  }

  close(): void {
    if (this.closed) return;
    this.closed = true;
    watchListeners.delete(this.listener);
    if (watchListeners.size === 0 && watchInterval) {
      clearInterval(watchInterval);
      watchInterval = null;
    }
  }
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function errorResponse(code: string, message: string, status: number): Response {
  return jsonResponse({ detail: { code, message } }, status);
}

function currentUserFromAuthHeader(headers: Headers): MockUser | undefined {
  const header = headers.get('Authorization') ?? '';
  const match = /^Bearer (.+)$/.exec(header);
  const userId = match ? tokens.get(match[1]) : undefined;
  return userId ? users.find((u) => u.id === userId) : undefined;
}

async function handleFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const { pathname } = new URL(url);
  const method = (init.method ?? 'GET').toUpperCase();
  const headers = new Headers(init.headers);
  const body = init.body ? JSON.parse(init.body as string) : undefined;
  const currentUser = currentUserFromAuthHeader(headers);

  if (method === 'POST' && pathname === '/auth/signup') {
    const username = String(body.username).trim();
    if (users.some((u) => u.username.toLowerCase() === username.toLowerCase())) {
      return errorResponse('USERNAME_TAKEN', `Username "${username}" is already taken.`, 409);
    }
    const user: MockUser = { id: nextId('user'), username, password: body.password };
    users.push(user);
    const token = nextId('token');
    tokens.set(token, user.id);
    return jsonResponse({ user: { id: user.id, username: user.username }, token }, 201);
  }

  if (method === 'POST' && pathname === '/auth/login') {
    const username = String(body.username).trim();
    const match = users.find(
      (u) => u.username.toLowerCase() === username.toLowerCase() && u.password === body.password,
    );
    if (!match) {
      return errorResponse('INVALID_CREDENTIALS', 'Invalid username or password.', 401);
    }
    const token = nextId('token');
    tokens.set(token, match.id);
    return jsonResponse({ user: { id: match.id, username: match.username }, token });
  }

  if (method === 'POST' && pathname === '/auth/logout') {
    if (!currentUser) {
      return jsonResponse({ detail: 'Not authenticated' }, 401);
    }
    const header = headers.get('Authorization') ?? '';
    const match = /^Bearer (.+)$/.exec(header);
    if (match) tokens.delete(match[1]);
    return new Response(null, { status: 204 });
  }

  if (method === 'GET' && pathname === '/auth/me') {
    return jsonResponse(currentUser ? { id: currentUser.id, username: currentUser.username } : null);
  }

  if (method === 'GET' && pathname === '/leaderboard') {
    return jsonResponse([...leaderboard].sort((a, b) => b.score - a.score));
  }

  if (method === 'POST' && pathname === '/leaderboard') {
    if (!currentUser) {
      return jsonResponse({ detail: 'Not authenticated' }, 401);
    }
    const entry: LeaderboardEntry = {
      id: nextId('score'),
      username: currentUser.username,
      score: Number(body.score),
      mode: body.mode as GameMode,
      achievedAt: new Date().toISOString(),
    };
    leaderboard.push(entry);
    leaderboard.sort((a, b) => b.score - a.score);
    return jsonResponse([...leaderboard]);
  }

  throw new Error(`mockServer: unhandled request ${method} ${pathname}`);
}

export function installMockBackend(): void {
  vi.stubGlobal('fetch', (url: string | URL, init?: RequestInit) => handleFetch(String(url), init));
  vi.stubGlobal('EventSource', MockEventSource);
}

/** Resets all in-memory state (users, tokens, leaderboard, bot/watch) to
 * freshly-seeded. Call between tests for isolation. */
export function resetMockBackend(): void {
  users = [];
  leaderboard = seedLeaderboard();
  tokens = new Map();

  if (watchInterval) {
    clearInterval(watchInterval);
    watchInterval = null;
  }
  watchListeners.clear();
  botGame = null;
}
