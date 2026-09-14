import { LeaderboardTable } from '../components/LeaderboardTable/LeaderboardTable';
import { useAuth } from '../context/AuthContext';
import { useLeaderboard } from '../hooks/useLeaderboard';

export function LeaderboardPage() {
  const { user } = useAuth();
  const { entries, loading } = useLeaderboard();

  return (
    <div className="page">
      <h1>Leaderboard</h1>
      <div className="card">
        {loading ? (
          <p className="muted">Loading leaderboard…</p>
        ) : (
          <LeaderboardTable entries={entries} currentUsername={user?.username} />
        )}
      </div>
    </div>
  );
}
