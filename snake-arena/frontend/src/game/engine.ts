import { BOARD_HEIGHT, BOARD_WIDTH, INITIAL_SNAKE_LENGTH, SCORE_PER_FOOD } from './constants';
import { placeFood } from './food';
import type { Rng } from './rng';
import type { BoardSize, Direction, GameMode, GameState, Point } from './types';

const OPPOSITE: Record<Direction, Direction> = {
  UP: 'DOWN',
  DOWN: 'UP',
  LEFT: 'RIGHT',
  RIGHT: 'LEFT',
};

const DELTA: Record<Direction, Point> = {
  UP: { x: 0, y: -1 },
  DOWN: { x: 0, y: 1 },
  LEFT: { x: -1, y: 0 },
  RIGHT: { x: 1, y: 0 },
};

export function isCollision(point: Point, body: Point[]): boolean {
  return body.some((segment) => segment.x === point.x && segment.y === point.y);
}

/**
 * Computes where the snake's head lands after moving one step in `dir`.
 * Returns 'DEAD' when walls mode and the move exits the board.
 */
export function nextHeadPosition(
  head: Point,
  dir: Direction,
  board: BoardSize,
  mode: GameMode,
): Point | 'DEAD' {
  const delta = DELTA[dir];
  const raw = { x: head.x + delta.x, y: head.y + delta.y };

  const outOfBounds = raw.x < 0 || raw.x >= board.width || raw.y < 0 || raw.y >= board.height;

  if (!outOfBounds) {
    return raw;
  }

  if (mode === 'walls') {
    return 'DEAD';
  }

  return {
    x: (raw.x + board.width) % board.width,
    y: (raw.y + board.height) % board.height,
  };
}

export function createInitialState(opts: {
  mode: GameMode;
  rng: Rng;
  board?: BoardSize;
}): GameState {
  const board = opts.board ?? { width: BOARD_WIDTH, height: BOARD_HEIGHT };
  const startY = Math.floor(board.height / 2);
  const startX = Math.floor(board.width / 2);

  const snake: Point[] = [];
  for (let i = 0; i < INITIAL_SNAKE_LENGTH; i += 1) {
    snake.push({ x: startX - i, y: startY });
  }

  const food = placeFood(snake, board, opts.rng);

  return {
    board,
    mode: opts.mode,
    snake,
    direction: 'RIGHT',
    pendingDirection: null,
    food,
    score: 0,
    status: 'idle',
    tickCount: 0,
  };
}

/**
 * Buffers a direction change to be applied on the next `step`. Ignores
 * an immediate 180-degree reversal (which would collide with the neck)
 * once the snake has more than one segment.
 */
export function setDirection(state: GameState, dir: Direction): GameState {
  if (state.status === 'game-over') {
    return state;
  }

  const current = state.pendingDirection ?? state.direction;
  if (state.snake.length > 1 && dir === OPPOSITE[current]) {
    return state;
  }

  return { ...state, pendingDirection: dir };
}

export function step(state: GameState, rng: Rng): GameState {
  if (state.status === 'game-over') {
    return state;
  }

  const direction = state.pendingDirection ?? state.direction;
  const head = state.snake[0];
  const nextHead = nextHeadPosition(head, direction, state.board, state.mode);

  if (nextHead === 'DEAD') {
    return { ...state, direction, pendingDirection: null, status: 'game-over' };
  }

  const ateFood = nextHead.x === state.food.x && nextHead.y === state.food.y;
  const bodyToCheck = ateFood ? state.snake : state.snake.slice(0, -1);

  if (isCollision(nextHead, bodyToCheck)) {
    return { ...state, direction, pendingDirection: null, status: 'game-over' };
  }

  const newSnake = [nextHead, ...(ateFood ? state.snake : state.snake.slice(0, -1))];
  const newFood = ateFood ? placeFood(newSnake, state.board, rng) : state.food;
  const newScore = ateFood ? state.score + SCORE_PER_FOOD : state.score;

  return {
    ...state,
    snake: newSnake,
    food: newFood,
    score: newScore,
    direction,
    pendingDirection: null,
    status: 'running',
    tickCount: state.tickCount + 1,
  };
}
