import { useEffect, useState } from 'react';
import { backendClient } from '../api/backendClient';
import type { GameState } from '../game/types';

/** Subscribes to the always-on demo bot's live game feed via the backend facade. */
export function useLiveGame(): GameState | null {
  const [state, setState] = useState<GameState | null>(null);

  useEffect(() => {
    const unsubscribe = backendClient.watch.subscribe(setState);
    return unsubscribe;
  }, []);

  return state;
}
