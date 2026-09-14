import { useCallback, useEffect, useState } from 'react';
import { backendClient } from '../api/backendClient';
import type { LeaderboardEntry } from '../api/types';
import { useAuth } from '../context/AuthContext';
import type { GameMode } from '../game/types';

export function useLeaderboard() {
  const { user } = useAuth();
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const result = await backendClient.leaderboard.getLeaderboard();
      setEntries(result);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const submitScore = useCallback(
    async (score: number, mode: GameMode) => {
      if (!user) return;
      const updated = await backendClient.leaderboard.submitScore({ username: user.username, score, mode });
      setEntries(updated);
    },
    [user],
  );

  return { entries, loading, refresh, submitScore };
}
