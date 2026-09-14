import type { GameMode } from '../game/types';
import type { LeaderboardEntry } from './types';

export interface DbUser {
  id: string;
  username: string;
  password: string;
}

interface MockDb {
  users: DbUser[];
  leaderboard: LeaderboardEntry[];
  currentUserId: string | null;
}

const WALLS: GameMode = 'walls';
const PASS_THROUGH: GameMode = 'pass-through';

function seedLeaderboard(): LeaderboardEntry[] {
  const entries: LeaderboardEntry[] = [
    { id: 'seed-1', username: 'PixelViper', score: 480, mode: WALLS, achievedAt: '2026-09-01T10:00:00.000Z' },
    { id: 'seed-2', username: 'GridMaster', score: 410, mode: PASS_THROUGH, achievedAt: '2026-09-02T10:00:00.000Z' },
    { id: 'seed-3', username: 'LoopHound', score: 360, mode: PASS_THROUGH, achievedAt: '2026-09-03T10:00:00.000Z' },
    { id: 'seed-4', username: 'ByteCoil', score: 300, mode: WALLS, achievedAt: '2026-09-04T10:00:00.000Z' },
    { id: 'seed-5', username: 'TailWhip', score: 250, mode: WALLS, achievedAt: '2026-09-05T10:00:00.000Z' },
    { id: 'seed-6', username: 'CrunchApple', score: 180, mode: PASS_THROUGH, achievedAt: '2026-09-06T10:00:00.000Z' },
    { id: 'seed-7', username: 'SlowSlither', score: 90, mode: WALLS, achievedAt: '2026-09-07T10:00:00.000Z' },
  ];
  return entries.sort((a, b) => b.score - a.score);
}

export const db: MockDb = {
  users: [],
  leaderboard: seedLeaderboard(),
  currentUserId: null,
};

/** Resets the in-memory mock database to its seeded state. Used between tests, and models the "no persistence across reload" auth decision. */
export function resetDb(): void {
  db.users = [];
  db.leaderboard = seedLeaderboard();
  db.currentUserId = null;
}
