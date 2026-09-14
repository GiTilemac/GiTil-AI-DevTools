import type { GameState } from '../game/types';
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

const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

interface AuthResponse {
  user: User;
  token: string;
}

// Bearer token for the current session. Deliberately kept in memory only
// (never localStorage) so a page reload still starts logged out, matching
// the product decision in spec §2.4/§3.9.
let authToken: string | null = null;

async function request<T>(path: string, init: RequestInit = {}, requireAuth = false): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) {
    headers.set('Content-Type', 'application/json');
  }
  if (requireAuth && authToken) {
    headers.set('Authorization', `Bearer ${authToken}`);
  }

  const response = await fetch(`${BASE_URL}${path}`, { ...init, headers });

  if (response.status === 204) {
    return undefined as T;
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    if (body && typeof body.detail === 'object' && body.detail?.code) {
      throw new BackendError(body.detail.code, body.detail.message);
    }
    throw new Error(`Request to ${path} failed with status ${response.status}`);
  }

  return body as T;
}

/**
 * The single facade for everything "backend". Pages, hooks, and context
 * only ever talk to this object — never call `fetch`/`EventSource`
 * directly — so the backend (mocked in tests, real over HTTP otherwise)
 * stays swappable behind this one file.
 */
export const backendClient = {
  auth: {
    async signup(input: SignupInput): Promise<User> {
      const { user, token } = await request<AuthResponse>('/auth/signup', {
        method: 'POST',
        body: JSON.stringify(input),
      });
      authToken = token;
      return user;
    },

    async login(input: LoginInput): Promise<User> {
      const { user, token } = await request<AuthResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(input),
      });
      authToken = token;
      return user;
    },

    async logout(): Promise<void> {
      if (!authToken) {
        return;
      }
      try {
        await request<void>('/auth/logout', { method: 'POST' }, true);
      } catch {
        // A 401 here just means the token was already invalid server-side
        // (e.g. stale/expired) - logout is idempotent either way.
      } finally {
        authToken = null;
      }
    },

    async getCurrentUser(): Promise<User | null> {
      return request<User | null>('/auth/me', {}, true);
    },
  },

  leaderboard: {
    async getLeaderboard(): Promise<LeaderboardEntry[]> {
      return request<LeaderboardEntry[]>('/leaderboard');
    },

    async submitScore(input: SubmitScoreInput): Promise<LeaderboardEntry[]> {
      return request<LeaderboardEntry[]>(
        '/leaderboard',
        { method: 'POST', body: JSON.stringify(input) },
        true,
      );
    },
  },

  watch: {
    /**
     * Subscribes to the live feed of the (single, always-on) demo bot's
     * game state via server-sent events. Fires immediately with the
     * current state, then again on every server tick, until the caller
     * unsubscribes (which closes the connection).
     */
    subscribe(onUpdate: (state: GameState) => void): () => void {
      const source = new EventSource(`${BASE_URL}/watch/live`);
      source.onmessage = (event) => {
        onUpdate(JSON.parse(event.data) as GameState);
      };
      return () => source.close();
    },
  },
};
