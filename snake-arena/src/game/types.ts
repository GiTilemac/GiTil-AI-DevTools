export type Point = { x: number; y: number };

export type Direction = 'UP' | 'DOWN' | 'LEFT' | 'RIGHT';

export type GameMode = 'pass-through' | 'walls';

export type GameStatus = 'idle' | 'running' | 'game-over';

export interface BoardSize {
  width: number;
  height: number;
}

export interface GameState {
  board: BoardSize;
  mode: GameMode;
  snake: Point[];
  direction: Direction;
  pendingDirection: Direction | null;
  food: Point;
  score: number;
  status: GameStatus;
  tickCount: number;
}
