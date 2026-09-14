import type { GameState } from '../../game/types';
import styles from './GameBoard.module.css';

const CELL_SIZE = 18;

export interface GameBoardProps {
  state: GameState;
}

/**
 * Pure renderer of a GameState — has no idea whether it's being driven
 * by keyboard input (Play) or a subscribed bot feed (Watch).
 */
export function GameBoard({ state }: GameBoardProps) {
  const { board, snake, food } = state;
  const cellKind = (x: number, y: number): 'food' | 'head' | 'body' | null => {
    if (food.x === x && food.y === y) return 'food';
    const headIndex = snake.findIndex((s) => s.x === x && s.y === y);
    if (headIndex === 0) return 'head';
    if (headIndex > 0) return 'body';
    return null;
  };
  const cellClass = (kind: 'food' | 'head' | 'body' | null): string => {
    if (kind === 'food') return styles.food;
    if (kind === 'head') return styles.snakeHead;
    if (kind === 'body') return styles.snakeBody;
    return '';
  };

  return (
    <div className={styles.wrapper}>
      <div
        className={styles.board}
        style={{
          gridTemplateColumns: `repeat(${board.width}, ${CELL_SIZE}px)`,
          gridTemplateRows: `repeat(${board.height}, ${CELL_SIZE}px)`,
        }}
        role="grid"
        aria-label="Snake game board"
        data-testid="game-board"
      >
        {Array.from({ length: board.height }).map((_, y) =>
          Array.from({ length: board.width }).map((_, x) => {
            const kind = cellKind(x, y);
            return (
              <div
                key={`${x}-${y}`}
                className={`${styles.cell} ${cellClass(kind)}`}
                data-cell={kind ?? undefined}
                data-coord={`${x},${y}`}
              />
            );
          }),
        )}
      </div>
      {state.status === 'game-over' && <div className={styles.gameOverBanner}>Game over</div>}
    </div>
  );
}
