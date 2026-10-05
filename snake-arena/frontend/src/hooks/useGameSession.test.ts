import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { backendClient } from '../api/backendClient';
import type { GameMode, GameStatus } from '../game/types';
import { HEARTBEAT_INTERVAL_MS, useGameSession } from './useGameSession';

async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

function render(status: GameStatus, mode: GameMode = 'walls') {
  return renderHook(({ status: s, mode: m }) => useGameSession(s, m), { initialProps: { status, mode } });
}

describe('useGameSession', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('does nothing until the game is running', async () => {
    const start = vi.spyOn(backendClient.games, 'start');
    render('idle');
    await flush();
    expect(start).not.toHaveBeenCalled();
  });

  it('starts a session when the game runs and ends it on game over', async () => {
    const start = vi.spyOn(backendClient.games, 'start');
    const end = vi.spyOn(backendClient.games, 'end');
    const hook = render('idle');

    hook.rerender({ status: 'running', mode: 'walls' });
    await flush();
    expect(start).toHaveBeenCalledWith('walls');
    const { id } = await start.mock.results[0].value;

    hook.rerender({ status: 'game-over', mode: 'walls' });
    await flush();
    expect(end).toHaveBeenCalledWith(id);
  });

  it('sends heartbeats while the game runs', async () => {
    const heartbeat = vi.spyOn(backendClient.games, 'heartbeat');
    render('running');
    await flush();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(HEARTBEAT_INTERVAL_MS * 2);
    });
    expect(heartbeat).toHaveBeenCalledTimes(2);
  });

  it('ends the session when the page is left mid-game', async () => {
    const end = vi.spyOn(backendClient.games, 'end');
    const hook = render('running');
    await flush();
    hook.unmount();
    await flush();
    expect(end).toHaveBeenCalledTimes(1);
  });

  it('never lets a failed start affect anything', async () => {
    vi.spyOn(backendClient.games, 'start').mockRejectedValue(new Error('backend down'));
    const heartbeat = vi.spyOn(backendClient.games, 'heartbeat');
    const end = vi.spyOn(backendClient.games, 'end');
    const hook = render('running');
    await flush();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(HEARTBEAT_INTERVAL_MS);
    });
    hook.rerender({ status: 'game-over', mode: 'walls' });
    await flush();
    expect(heartbeat).not.toHaveBeenCalled();
    expect(end).not.toHaveBeenCalled();
  });
});
