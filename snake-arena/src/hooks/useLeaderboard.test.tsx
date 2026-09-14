import { act, renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { useLeaderboard } from './useLeaderboard';

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe('useLeaderboard', () => {
  it('loads entries on mount', async () => {
    const { result } = renderHook(() => useLeaderboard(), { wrapper });
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.entries.length).toBeGreaterThan(0);
  });

  it('submitScore updates and re-sorts local entries for a logged-in user', async () => {
    const { result } = renderHook(
      () => ({ auth: useAuth(), leaderboard: useLeaderboard() }),
      { wrapper },
    );

    await waitFor(() => expect(result.current.leaderboard.loading).toBe(false));

    await act(async () => {
      await result.current.auth.signup({ username: 'topscorer', password: 'pw' });
    });

    const topScore = result.current.leaderboard.entries[0].score;

    await act(async () => {
      await result.current.leaderboard.submitScore(topScore + 100, 'walls');
    });

    expect(result.current.leaderboard.entries[0].username).toBe('topscorer');
    expect(result.current.leaderboard.entries[0].score).toBe(topScore + 100);
  });

  it('is a no-op when no user is logged in', async () => {
    const { result } = renderHook(() => useLeaderboard(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    const before = result.current.entries;

    await act(async () => {
      await result.current.submitScore(9999, 'walls');
    });

    expect(result.current.entries).toBe(before);
  });
});
