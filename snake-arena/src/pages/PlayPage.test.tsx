import { act, fireEvent, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuth } from '../context/AuthContext';
import { renderWithProviders } from '../test/test-utils';
import { PlayPage } from './PlayPage';

function LoggedInPlayPage({ username }: { username: string }) {
  const { signup, user } = useAuth();
  if (!user) {
    return (
      <button type="button" onClick={() => signup({ username, password: 'pw' })}>
        log in as {username}
      </button>
    );
  }
  return <PlayPage />;
}

async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
    await Promise.resolve();
  });
}

describe('PlayPage', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the mode selector and the game board', () => {
    renderWithProviders(<PlayPage />, { route: '/play' });
    expect(screen.getByRole('radiogroup', { name: /game mode/i })).toBeInTheDocument();
    expect(screen.getByTestId('game-board')).toBeInTheDocument();
  });

  it('lets you switch modes before starting, updating the active selection', () => {
    renderWithProviders(<PlayPage />, { route: '/play' });

    const passThroughBtn = screen.getByRole('radio', { name: 'Pass-through' });
    const wallsBtn = screen.getByRole('radio', { name: 'Walls' });
    expect(passThroughBtn).toHaveAttribute('aria-checked', 'true');

    fireEvent.click(wallsBtn);

    expect(wallsBtn).toHaveAttribute('aria-checked', 'true');
    expect(passThroughBtn).toHaveAttribute('aria-checked', 'false');
  });

  it('moves the snake head in response to arrow key presses once a tick elapses', async () => {
    renderWithProviders(<PlayPage />, { route: '/play' });

    const headBefore = document.querySelector('[data-cell="head"]')!.getAttribute('data-coord');

    fireEvent.keyDown(window, { key: 'ArrowDown' });
    await advance(150);

    const headAfter = document.querySelector('[data-cell="head"]')!.getAttribute('data-coord');
    expect(headAfter).not.toBe(headBefore);
  });

  it('submits the score and shows a confirmation when a logged-in player finishes a game', async () => {
    renderWithProviders(<LoggedInPlayPage username="scoretester" />, { route: '/play' });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /log in as scoretester/i }));
    });

    fireEvent.click(screen.getByRole('radio', { name: 'Walls' }));

    fireEvent.keyDown(window, { key: 'ArrowRight' });
    // Snake starts centered (x=10 of 20) heading right; 10 ticks drives it into the wall.
    await advance(150 * 12);

    expect(screen.getByText(/score submitted/i)).toBeInTheDocument();
  });

  it('shows a login prompt instead of submitting when a guest finishes a game', async () => {
    renderWithProviders(<PlayPage />, { route: '/play' });

    fireEvent.click(screen.getByRole('radio', { name: 'Walls' }));

    fireEvent.keyDown(window, { key: 'ArrowRight' });
    await advance(150 * 12);

    expect(screen.getByText(/to save your score/i)).toBeInTheDocument();
  });
});
