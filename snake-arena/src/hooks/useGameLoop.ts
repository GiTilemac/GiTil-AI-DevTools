import { useCallback, useEffect, useRef, useState } from 'react';
import { TICK_INTERVAL_MS } from '../game/constants';
import { createInitialState, setDirection, step } from '../game/engine';
import { createRng, type Rng } from '../game/rng';
import type { Direction, GameMode, GameState } from '../game/types';

const KEY_TO_DIRECTION: Record<string, Direction> = {
  ArrowUp: 'UP',
  ArrowDown: 'DOWN',
  ArrowLeft: 'LEFT',
  ArrowRight: 'RIGHT',
  w: 'UP',
  W: 'UP',
  s: 'DOWN',
  S: 'DOWN',
  a: 'LEFT',
  A: 'LEFT',
  d: 'RIGHT',
  D: 'RIGHT',
};

export interface UseGameLoopOptions {
  seed?: number;
}

/** Drives the interactive Play screen: keyboard input, tick interval, and mode/restart control, on top of the pure game/engine reducer. */
export function useGameLoop(initialMode: GameMode, opts: UseGameLoopOptions = {}) {
  const makeRng = useCallback((): Rng => createRng(opts.seed ?? Date.now()), [opts.seed]);
  const rngRef = useRef<Rng>(makeRng());
  const [state, setState] = useState<GameState>(() =>
    createInitialState({ mode: initialMode, rng: rngRef.current }),
  );

  const changeDirection = useCallback((dir: Direction) => {
    setState((prev) => {
      const next = setDirection(prev, dir);
      return next.status === 'idle' ? { ...next, status: 'running' } : next;
    });
  }, []);

  const setMode = useCallback(
    (mode: GameMode) => {
      setState((prev) => {
        if (prev.status === 'running') return prev;
        rngRef.current = makeRng();
        return createInitialState({ mode, rng: rngRef.current });
      });
    },
    [makeRng],
  );

  const restart = useCallback(() => {
    setState((prev) => {
      rngRef.current = makeRng();
      return createInitialState({ mode: prev.mode, rng: rngRef.current });
    });
  }, [makeRng]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const dir = KEY_TO_DIRECTION[event.key];
      if (dir) {
        event.preventDefault();
        changeDirection(dir);
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [changeDirection]);

  useEffect(() => {
    if (state.status !== 'running') return undefined;
    const id = setInterval(() => {
      setState((prev) => step(prev, rngRef.current));
    }, TICK_INTERVAL_MS);
    return () => clearInterval(id);
  }, [state.status]);

  return { state, changeDirection, setMode, restart };
}
