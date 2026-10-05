import { useEffect } from 'react';
import { backendClient } from '../api/backendClient';
import type { GameMode, GameStatus } from '../game/types';

/** How often a running game tells the backend it's still being played. The backend expires sessions after 2 minutes without one. */
export const HEARTBEAT_INTERVAL_MS = 30_000;

/**
 * Reports the Play screen's game lifecycle to the backend for its game
 * metrics: starts a session when the game starts running, sends
 * heartbeats while it runs, and ends it when the game stops running (game
 * over, restart, or leaving the page). Best effort - every failure is
 * swallowed so it can never affect play.
 *
 * (Under React StrictMode in development, effects run twice, so each game
 * start opens and immediately closes an extra session there.)
 */
export function useGameSession(status: GameStatus, mode: GameMode): void {
  useEffect(() => {
    if (status !== 'running') return undefined;

    const session = backendClient.games
      .start(mode)
      .then((s) => s.id)
      .catch(() => null);

    const heartbeat = setInterval(() => {
      void session.then((id) => (id ? backendClient.games.heartbeat(id) : undefined)).catch(() => undefined);
    }, HEARTBEAT_INTERVAL_MS);

    return () => {
      clearInterval(heartbeat);
      void session.then((id) => (id ? backendClient.games.end(id) : undefined)).catch(() => undefined);
    };
  }, [status, mode]);
}
