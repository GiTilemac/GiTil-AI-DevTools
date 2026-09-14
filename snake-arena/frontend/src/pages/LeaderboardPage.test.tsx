import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { useAuth } from '../context/AuthContext';
import { renderWithProviders } from '../test/test-utils';
import { LeaderboardPage } from './LeaderboardPage';

function LoggedInLeaderboard({ username }: { username: string }) {
  const { signup } = useAuth();
  return (
    <div>
      <button type="button" onClick={() => signup({ username, password: 'pw' })}>
        log in as {username}
      </button>
      <LeaderboardPage />
    </div>
  );
}

describe('LeaderboardPage', () => {
  it('shows a loading state before data resolves, then renders sorted entries', async () => {
    renderWithProviders(<LeaderboardPage />, { route: '/leaderboard' });

    const rows = await screen.findAllByRole('row');
    // header row + at least one data row
    expect(rows.length).toBeGreaterThan(1);

    const scoreCells = (await screen.findAllByRole('row'))
      .slice(1)
      .map((row) => Number(row.querySelectorAll('td')[2].textContent));
    for (let i = 1; i < scoreCells.length; i += 1) {
      expect(scoreCells[i - 1]).toBeGreaterThanOrEqual(scoreCells[i]);
    }
  });

  it('highlights the logged-in user row once they appear on the board', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoggedInLeaderboard username="PixelViper" />, { route: '/leaderboard' });

    await screen.findAllByRole('row');
    await user.click(screen.getByText(/log in as PixelViper/i));

    const row = await screen.findByText('PixelViper');
    expect(row.closest('tr')).toHaveAttribute('data-current-user', 'true');
  });
});
