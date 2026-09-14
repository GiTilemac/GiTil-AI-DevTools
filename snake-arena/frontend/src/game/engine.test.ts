import { describe, expect, it } from 'vitest';
import { createInitialState, isCollision, nextHeadPosition, setDirection, step } from './engine';
import { createRng } from './rng';
import type { GameState } from './types';

describe('createInitialState', () => {
  it('creates a snake of the configured initial length, centered, facing right', () => {
    const state = createInitialState({ mode: 'walls', rng: createRng(1) });
    expect(state.snake).toHaveLength(3);
    expect(state.direction).toBe('RIGHT');
    expect(state.status).toBe('idle');
    expect(state.score).toBe(0);
  });

  it('places food off the snake', () => {
    const state = createInitialState({ mode: 'walls', rng: createRng(1) });
    const onSnake = state.snake.some((s) => s.x === state.food.x && s.y === state.food.y);
    expect(onSnake).toBe(false);
  });
});

describe('nextHeadPosition', () => {
  const board = { width: 5, height: 5 };

  it('moves within bounds normally', () => {
    expect(nextHeadPosition({ x: 2, y: 2 }, 'RIGHT', board, 'walls')).toEqual({ x: 3, y: 2 });
  });

  it('wraps around edges in pass-through mode', () => {
    expect(nextHeadPosition({ x: 4, y: 2 }, 'RIGHT', board, 'pass-through')).toEqual({ x: 0, y: 2 });
    expect(nextHeadPosition({ x: 0, y: 2 }, 'LEFT', board, 'pass-through')).toEqual({ x: 4, y: 2 });
  });

  it('returns DEAD on boundary exit in walls mode', () => {
    expect(nextHeadPosition({ x: 4, y: 2 }, 'RIGHT', board, 'walls')).toBe('DEAD');
    expect(nextHeadPosition({ x: 0, y: 0 }, 'UP', board, 'walls')).toBe('DEAD');
  });
});

describe('isCollision', () => {
  it('detects a point matching any body segment', () => {
    const body = [{ x: 1, y: 1 }, { x: 2, y: 1 }];
    expect(isCollision({ x: 2, y: 1 }, body)).toBe(true);
    expect(isCollision({ x: 9, y: 9 }, body)).toBe(false);
  });
});

describe('setDirection', () => {
  function baseState(): GameState {
    return createInitialState({ mode: 'walls', rng: createRng(1) });
  }

  it('buffers a valid direction change', () => {
    const state = setDirection(baseState(), 'UP');
    expect(state.pendingDirection).toBe('UP');
  });

  it('ignores an immediate 180-degree reversal', () => {
    const state = setDirection(baseState(), 'LEFT');
    expect(state.pendingDirection).toBeNull();
  });

  it('is a no-op once the game is over', () => {
    const state = { ...baseState(), status: 'game-over' as const };
    const result = setDirection(state, 'UP');
    expect(result).toBe(state);
  });
});

describe('step', () => {
  it('moves the head one cell in the current direction', () => {
    const rng = createRng(1);
    const initial = createInitialState({ mode: 'walls', rng });
    const head = initial.snake[0];
    const next = step(initial, rng);
    expect(next.snake[0]).toEqual({ x: head.x + 1, y: head.y });
    expect(next.status).toBe('running');
  });

  it('applies a buffered direction change before moving', () => {
    const rng = createRng(1);
    const initial = createInitialState({ mode: 'walls', rng });
    const turned = setDirection(initial, 'DOWN');
    const next = step(turned, rng);
    expect(next.direction).toBe('DOWN');
    expect(next.pendingDirection).toBeNull();
  });

  it('ends the game when hitting a wall in walls mode', () => {
    const rng = createRng(1);
    const board = { width: 5, height: 5 };
    let state = createInitialState({ mode: 'walls', rng, board });
    state = { ...state, snake: [{ x: 4, y: 2 }, { x: 3, y: 2 }, { x: 2, y: 2 }], direction: 'RIGHT' };
    const next = step(state, rng);
    expect(next.status).toBe('game-over');
  });

  it('wraps around instead of dying in pass-through mode', () => {
    const rng = createRng(1);
    const board = { width: 5, height: 5 };
    let state = createInitialState({ mode: 'pass-through', rng, board });
    state = { ...state, snake: [{ x: 4, y: 2 }, { x: 3, y: 2 }, { x: 2, y: 2 }], direction: 'RIGHT' };
    const next = step(state, rng);
    expect(next.status).toBe('running');
    expect(next.snake[0]).toEqual({ x: 0, y: 2 });
  });

  it('ends the game on self-collision', () => {
    const rng = createRng(1);
    const board = { width: 10, height: 10 };
    let state = createInitialState({ mode: 'walls', rng, board });
    // Head at (5,5) moving UP lands on (5,4), which is body segment index 2
    // (not the tail, which moves out of the way) -> must be a collision.
    state = {
      ...state,
      snake: [
        { x: 5, y: 5 },
        { x: 9, y: 9 },
        { x: 5, y: 4 },
        { x: 1, y: 1 },
        { x: 0, y: 0 },
      ],
      direction: 'UP',
      food: { x: 8, y: 8 },
    };
    const next = step(state, rng);
    expect(next.status).toBe('game-over');
  });

  it('grows the snake, increases the score, and relocates food when eating', () => {
    const rng = createRng(1);
    const board = { width: 10, height: 10 };
    let state = createInitialState({ mode: 'walls', rng, board });
    state = {
      ...state,
      snake: [{ x: 5, y: 5 }, { x: 4, y: 5 }, { x: 3, y: 5 }],
      direction: 'RIGHT',
      food: { x: 6, y: 5 },
    };
    const lengthBefore = state.snake.length;
    const next = step(state, rng);
    expect(next.snake).toHaveLength(lengthBefore + 1);
    expect(next.score).toBe(10);
    expect(next.food).not.toEqual({ x: 6, y: 5 });
  });

  it('does not grow when not eating (tail follows)', () => {
    const rng = createRng(1);
    const board = { width: 10, height: 10 };
    let state = createInitialState({ mode: 'walls', rng, board });
    state = {
      ...state,
      snake: [{ x: 5, y: 5 }, { x: 4, y: 5 }, { x: 3, y: 5 }],
      direction: 'RIGHT',
      food: { x: 9, y: 9 },
    };
    const next = step(state, rng);
    expect(next.snake).toHaveLength(3);
    expect(next.score).toBe(0);
  });

  it('is a no-op once the game is over', () => {
    const rng = createRng(1);
    const state = { ...createInitialState({ mode: 'walls', rng }), status: 'game-over' as const };
    const next = step(state, rng);
    expect(next).toBe(state);
  });
});
