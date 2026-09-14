import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { resetWatchState } from '../api/backendClient';
import { useLiveGame } from './useLiveGame';

describe('useLiveGame', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    resetWatchState();
  });

  it('starts null, then receives a GameState', async () => {
    const { result } = renderHook(() => useLiveGame());
    expect(result.current).not.toBeNull();
    expect(result.current?.status).toBe('running');
  });

  it('updates state on each simulated tick', async () => {
    const { result } = renderHook(() => useLiveGame());
    const firstTick = result.current?.tickCount ?? 0;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(150);
    });

    expect(result.current?.tickCount).toBeGreaterThan(firstTick);
  });

  it('stops updating after unmount', async () => {
    const { result, unmount } = renderHook(() => useLiveGame());
    const tickAtUnmount = result.current?.tickCount ?? 0;
    unmount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(600);
    });
    expect(result.current?.tickCount).toBe(tickAtUnmount);
  });
});
