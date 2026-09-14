import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useLiveGame } from './useLiveGame';

describe('useLiveGame', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts null, then receives a GameState', async () => {
    const { result } = renderHook(() => useLiveGame());
    expect(result.current).toBeNull();

    // The initial state arrives over a (mocked) SSE connection, which
    // delivers it a microtask after subscribing rather than synchronously.
    await act(async () => {});

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
    await act(async () => {}); // let the initial SSE message arrive
    const tickAtUnmount = result.current?.tickCount ?? 0;
    unmount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(600);
    });
    expect(result.current?.tickCount).toBe(tickAtUnmount);
  });
});
