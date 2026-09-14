import { describe, expect, it } from 'vitest';
import { placeFood } from './food';
import { createRng } from './rng';
import type { Point } from './types';

describe('placeFood', () => {
  it('never places food on an occupied cell', () => {
    const occupied: Point[] = [
      { x: 0, y: 0 },
      { x: 1, y: 0 },
      { x: 2, y: 0 },
    ];
    const rng = createRng(1);
    for (let i = 0; i < 200; i += 1) {
      const food = placeFood(occupied, { width: 20, height: 20 }, rng);
      expect(occupied.some((p) => p.x === food.x && p.y === food.y)).toBe(false);
    }
  });

  it('is deterministic for a given rng stream', () => {
    const occupied: Point[] = [{ x: 5, y: 5 }];
    const a = placeFood(occupied, { width: 10, height: 10 }, createRng(99));
    const b = placeFood(occupied, { width: 10, height: 10 }, createRng(99));
    expect(a).toEqual(b);
  });

  it('falls back to scanning free cells when the board is nearly full', () => {
    const board = { width: 3, height: 1 };
    const occupied: Point[] = [
      { x: 0, y: 0 },
      { x: 1, y: 0 },
    ];
    const rng = createRng(5);
    const food = placeFood(occupied, board, rng);
    expect(food).toEqual({ x: 2, y: 0 });
  });

  it('throws when there are no free cells left', () => {
    const board = { width: 2, height: 1 };
    const occupied: Point[] = [
      { x: 0, y: 0 },
      { x: 1, y: 0 },
    ];
    const rng = createRng(3);
    expect(() => placeFood(occupied, board, rng)).toThrow();
  });
});
