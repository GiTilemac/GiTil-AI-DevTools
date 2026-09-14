import type { BoardSize, Point } from './types';
import type { Rng } from './rng';

function isOccupied(point: Point, occupied: Point[]): boolean {
  return occupied.some((p) => p.x === point.x && p.y === point.y);
}

/**
 * Picks a free cell for the next food item. Rejection-samples random
 * cells first (fast path); if the board is nearly full, falls back to
 * scanning all free cells so this never returns an occupied cell.
 */
export function placeFood(occupied: Point[], board: BoardSize, rng: Rng): Point {
  const maxAttempts = 100;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const candidate: Point = {
      x: Math.floor(rng() * board.width),
      y: Math.floor(rng() * board.height),
    };
    if (!isOccupied(candidate, occupied)) {
      return candidate;
    }
  }

  const freeCells: Point[] = [];
  for (let y = 0; y < board.height; y += 1) {
    for (let x = 0; x < board.width; x += 1) {
      const cell = { x, y };
      if (!isOccupied(cell, occupied)) {
        freeCells.push(cell);
      }
    }
  }

  if (freeCells.length === 0) {
    throw new Error('placeFood: no free cells remain on the board');
  }

  const index = Math.floor(rng() * freeCells.length) % freeCells.length;
  return freeCells[index];
}
