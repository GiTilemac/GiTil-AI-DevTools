import { act, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../test/test-utils';
import { WatchPage } from './WatchPage';

describe('WatchPage', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('shows Connecting… first, then a live board once the bot state arrives', async () => {
    renderWithProviders(<WatchPage />, { route: '/watch' });
    expect(screen.getByText(/Connecting/)).toBeInTheDocument();

    // The initial state arrives over a (mocked) SSE connection, which
    // delivers it a microtask after subscribing rather than synchronously.
    await act(async () => {});

    expect(screen.getByTestId('game-board')).toBeInTheDocument();
    expect(screen.getByText(/SnakeBot/)).toBeInTheDocument();
  });

  it('updates the board content between two consecutive ticks', async () => {
    renderWithProviders(<WatchPage />, { route: '/watch' });
    await act(async () => {}); // let the initial SSE message arrive
    const boardBefore = screen.getByTestId('game-board').innerHTML;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(150);
    });

    const boardAfter = screen.getByTestId('game-board').innerHTML;
    expect(boardAfter).not.toBe(boardBefore);
  });
});
