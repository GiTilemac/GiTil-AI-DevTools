import type { LeaderboardEntry } from '../../api/types';
import styles from './LeaderboardTable.module.css';

export interface LeaderboardTableProps {
  entries: LeaderboardEntry[];
  currentUsername?: string | null;
}

export function LeaderboardTable({ entries, currentUsername }: LeaderboardTableProps) {
  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th className={styles.rank}>#</th>
          <th>Player</th>
          <th>Score</th>
          <th>Mode</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry, index) => (
          <tr
            key={entry.id}
            className={entry.username === currentUsername ? styles.currentUserRow : ''}
            data-current-user={entry.username === currentUsername ? 'true' : undefined}
          >
            <td className={styles.rank}>{index + 1}</td>
            <td>{entry.username}</td>
            <td>{entry.score}</td>
            <td>
              <span className={styles.modeBadge}>{entry.mode}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
