import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { backendClient, BackendError, resetWatchState } from './backendClient';
import { resetDb } from './mockDb';

describe('backendClient.auth', () => {
  it('signup creates a user and logs them in', async () => {
    const user = await backendClient.auth.signup({ username: 'newbie', password: 'pw' });
    expect(user.username).toBe('newbie');
    const current = await backendClient.auth.getCurrentUser();
    expect(current?.username).toBe('newbie');
  });

  it('rejects signup with a duplicate username', async () => {
    await backendClient.auth.signup({ username: 'taken', password: 'pw' });
    await expect(backendClient.auth.signup({ username: 'taken', password: 'other' })).rejects.toMatchObject({
      code: 'USERNAME_TAKEN',
    });
  });

  it('rejects signup with a case-insensitive duplicate username', async () => {
    await backendClient.auth.signup({ username: 'CaseTest', password: 'pw' });
    await expect(backendClient.auth.signup({ username: 'casetest', password: 'pw' })).rejects.toBeInstanceOf(
      BackendError,
    );
  });

  it('rejects login with wrong credentials', async () => {
    await backendClient.auth.signup({ username: 'someone', password: 'correct' });
    await backendClient.auth.logout();
    await expect(backendClient.auth.login({ username: 'someone', password: 'wrong' })).rejects.toMatchObject({
      code: 'INVALID_CREDENTIALS',
    });
  });

  it('logs a user in with correct credentials', async () => {
    await backendClient.auth.signup({ username: 'logintest', password: 'secret' });
    await backendClient.auth.logout();
    const user = await backendClient.auth.login({ username: 'logintest', password: 'secret' });
    expect(user.username).toBe('logintest');
  });

  it('logout clears the current user', async () => {
    await backendClient.auth.signup({ username: 'logout-me', password: 'pw' });
    await backendClient.auth.logout();
    const current = await backendClient.auth.getCurrentUser();
    expect(current).toBeNull();
  });

  it('getCurrentUser is null when nobody is logged in', async () => {
    const current = await backendClient.auth.getCurrentUser();
    expect(current).toBeNull();
  });
});

describe('backendClient.leaderboard', () => {
  it('returns seeded entries pre-sorted descending', async () => {
    const entries = await backendClient.leaderboard.getLeaderboard();
    expect(entries.length).toBeGreaterThan(0);
    for (let i = 1; i < entries.length; i += 1) {
      expect(entries[i - 1].score).toBeGreaterThanOrEqual(entries[i].score);
    }
  });

  it('submitScore inserts a new entry and re-sorts the board', async () => {
    const before = await backendClient.leaderboard.getLeaderboard();
    const topScore = before[0].score;
    const updated = await backendClient.leaderboard.submitScore({
      username: 'challenger',
      score: topScore + 50,
      mode: 'walls',
    });
    expect(updated[0].username).toBe('challenger');
    expect(updated[0].score).toBe(topScore + 50);
  });
});

describe('backendClient.watch', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    resetDb();
    resetWatchState();
  });

  it('fires immediately on subscribe and again on each simulated tick', () => {
    const updates: number[] = [];
    const unsubscribe = backendClient.watch.subscribe((state) => {
      updates.push(state.tickCount);
    });

    expect(updates).toHaveLength(1);

    vi.advanceTimersByTime(150);
    expect(updates.length).toBeGreaterThanOrEqual(2);

    vi.advanceTimersByTime(150);
    expect(updates.length).toBeGreaterThanOrEqual(3);

    unsubscribe();
  });

  it('stops delivering updates after unsubscribe', () => {
    const updates: number[] = [];
    const unsubscribe = backendClient.watch.subscribe((state) => {
      updates.push(state.tickCount);
    });
    vi.advanceTimersByTime(150);
    const countAtUnsubscribe = updates.length;
    unsubscribe();
    vi.advanceTimersByTime(600);
    expect(updates.length).toBe(countAtUnsubscribe);
  });
});
