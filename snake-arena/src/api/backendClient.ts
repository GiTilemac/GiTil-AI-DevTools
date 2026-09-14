import { advanceBotGame, createBotGame, type BotGame } from '../game/bot';
import { TICK_INTERVAL_MS } from '../game/constants';
import type { GameMode, GameState } from '../game/types';
import { delay } from './latency';
import { db } from './mockDb';
import type { LeaderboardEntry, LoginInput, SignupInput, SubmitScoreInput, User } from './types';

export type BackendErrorCode = 'USERNAME_TAKEN' | 'INVALID_CREDENTIALS';

export class BackendError extends Error {
  code: BackendErrorCode;

  constructor(code: BackendErrorCode, message: string) {
    super(message);
    this.name = 'BackendError';
    this.code = code;
  }
}

function toUser(id: string, username: string): User {
  return { id, username };
}

function nextId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

let botGame: BotGame | null = null;
let watchInterval: ReturnType<typeof setInterval> | null = null;
const watchSubscribers = new Set<(state: GameState) => void>();

function tickWatch(): void {
  if (!botGame) return;
  botGame = advanceBotGame(botGame);
  watchSubscribers.forEach((cb) => cb(botGame!.state));
}

/**
 * The single facade for everything "backend". Pages, hooks, and context
 * only ever talk to this object — never to mockDb/game internals directly
 * — so swapping in a real HTTP backend later only touches this file.
 */
export const backendClient = {
  auth: {
    async signup(input: SignupInput): Promise<User> {
      const username = input.username.trim();
      if (db.users.some((u) => u.username.toLowerCase() === username.toLowerCase())) {
        throw new BackendError('USERNAME_TAKEN', `Username "${username}" is already taken.`);
      }
      const user = { id: nextId('user'), username, password: input.password };
      db.users.push(user);
      db.currentUserId = user.id;
      return delay(toUser(user.id, user.username));
    },

    async login(input: LoginInput): Promise<User> {
      const username = input.username.trim();
      const match = db.users.find(
        (u) => u.username.toLowerCase() === username.toLowerCase() && u.password === input.password,
      );
      if (!match) {
        throw new BackendError('INVALID_CREDENTIALS', 'Invalid username or password.');
      }
      db.currentUserId = match.id;
      return delay(toUser(match.id, match.username));
    },

    async logout(): Promise<void> {
      db.currentUserId = null;
      return delay(undefined);
    },

    async getCurrentUser(): Promise<User | null> {
      const match = db.users.find((u) => u.id === db.currentUserId);
      return delay(match ? toUser(match.id, match.username) : null);
    },
  },

  leaderboard: {
    async getLeaderboard(): Promise<LeaderboardEntry[]> {
      const sorted = [...db.leaderboard].sort((a, b) => b.score - a.score);
      return delay(sorted);
    },

    async submitScore(input: SubmitScoreInput): Promise<LeaderboardEntry[]> {
      const entry: LeaderboardEntry = {
        id: nextId('score'),
        username: input.username,
        score: input.score,
        mode: input.mode as GameMode,
        achievedAt: new Date().toISOString(),
      };
      db.leaderboard.push(entry);
      db.leaderboard.sort((a, b) => b.score - a.score);
      return delay([...db.leaderboard]);
    },
  },

  watch: {
    /**
     * Subscribes to a live feed of the (single, always-on) demo bot's
     * game state. Fires immediately with the current state, then on
     * every simulated tick. A single shared interval drives all
     * subscribers; it starts on the first subscriber and stops when
     * the last one unsubscribes.
     */
    subscribe(onUpdate: (state: GameState) => void, intervalMs: number = TICK_INTERVAL_MS): () => void {
      if (!botGame) {
        botGame = createBotGame();
      }
      watchSubscribers.add(onUpdate);
      onUpdate(botGame.state);

      if (!watchInterval) {
        watchInterval = setInterval(tickWatch, intervalMs);
      }

      return () => {
        watchSubscribers.delete(onUpdate);
        if (watchSubscribers.size === 0 && watchInterval) {
          clearInterval(watchInterval);
          watchInterval = null;
        }
      };
    },
  },
};

/** Resets the shared bot-watch state. Used between tests for isolation. */
export function resetWatchState(): void {
  if (watchInterval) {
    clearInterval(watchInterval);
    watchInterval = null;
  }
  watchSubscribers.clear();
  botGame = null;
}
