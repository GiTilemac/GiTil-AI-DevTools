import { BOT_RESTART_DELAY_TICKS } from './constants';
import { createInitialState, nextHeadPosition, setDirection, step } from './engine';
import { createRng, type Rng } from './rng';
import type { Direction, GameState } from './types';

export interface BotGame {
  state: GameState;
  rng: Rng;
  restartCountdown: number | null;
}

const ALL_DIRECTIONS: Direction[] = ['UP', 'DOWN', 'LEFT', 'RIGHT'];
const OPPOSITE: Record<Direction, Direction> = {
  UP: 'DOWN',
  DOWN: 'UP',
  LEFT: 'RIGHT',
  RIGHT: 'LEFT',
};

function manhattan(a: { x: number; y: number }, b: { x: number; y: number }): number {
  return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}

/**
 * Greedy bot: among directions that don't reverse into the neck, pick
 * the one that gets closest to the food while not immediately dying
 * (wall exit in walls mode, or self-collision). Falls back to any safe
 * direction, and finally to the current direction if nothing is safe
 * (the bot may die — that's expected and handled by the restart flow).
 */
export function decideDirection(state: GameState): Direction {
  const head = state.snake[0];
  const body = state.snake.slice(0, -1);

  const candidates = ALL_DIRECTIONS.filter((dir) => {
    if (state.snake.length > 1 && dir === OPPOSITE[state.direction]) {
      return false;
    }
    const next = nextHeadPosition(head, dir, state.board, state.mode);
    return next !== 'DEAD' && !body.some((s) => s.x === next.x && s.y === next.y);
  });

  if (candidates.length === 0) {
    return state.direction;
  }

  candidates.sort((a, b) => {
    const nextA = nextHeadPosition(head, a, state.board, state.mode);
    const nextB = nextHeadPosition(head, b, state.board, state.mode);
    const distA = nextA === 'DEAD' ? Infinity : manhattan(nextA, state.food);
    const distB = nextB === 'DEAD' ? Infinity : manhattan(nextB, state.food);
    return distA - distB;
  });

  return candidates[0];
}

export function createBotGame(seed = Date.now()): BotGame {
  const rng = createRng(seed);
  const state = createInitialState({ mode: 'pass-through', rng });
  return { state: { ...state, status: 'running' }, rng, restartCountdown: null };
}

/**
 * Advances the bot game by one tick. When the bot's game has ended,
 * counts down BOT_RESTART_DELAY_TICKS before starting a fresh game on
 * the same rng stream, so the Watch screen always has something live
 * to show.
 */
export function advanceBotGame(game: BotGame): BotGame {
  if (game.state.status === 'game-over') {
    const remaining = (game.restartCountdown ?? BOT_RESTART_DELAY_TICKS) - 1;
    if (remaining <= 0) {
      const freshState = createInitialState({ mode: game.state.mode, rng: game.rng });
      return { state: { ...freshState, status: 'running' }, rng: game.rng, restartCountdown: null };
    }
    return { ...game, restartCountdown: remaining };
  }

  const dir = decideDirection(game.state);
  const directed = setDirection(game.state, dir);
  const nextState = step(directed, game.rng);
  return { state: nextState, rng: game.rng, restartCountdown: null };
}
