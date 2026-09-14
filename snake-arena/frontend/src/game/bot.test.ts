import { describe, expect, it } from 'vitest';
import { advanceBotGame, createBotGame, decideDirection } from './bot';
import { BOT_RESTART_DELAY_TICKS } from './constants';

const OPPOSITE = { UP: 'DOWN', DOWN: 'UP', LEFT: 'RIGHT', RIGHT: 'LEFT' } as const;

describe('decideDirection', () => {
  it('never returns the direct reverse of the current direction', () => {
    let game = createBotGame(1);
    for (let i = 0; i < 300; i += 1) {
      if (game.state.status === 'running') {
        const dir = decideDirection(game.state);
        expect(dir).not.toBe(OPPOSITE[game.state.direction]);
      }
      game = advanceBotGame(game);
    }
  });
});

describe('advanceBotGame', () => {
  it('runs hundreds of ticks without throwing', () => {
    let game = createBotGame(42);
    expect(() => {
      for (let i = 0; i < 500; i += 1) {
        game = advanceBotGame(game);
      }
    }).not.toThrow();
  });

  it('restarts with a fresh, running game exactly after BOT_RESTART_DELAY_TICKS following a game-over', () => {
    let game = createBotGame(7);

    // Force a game-over deterministically instead of hoping the bot dies naturally.
    game = { ...game, state: { ...game.state, status: 'game-over' } };

    for (let i = 0; i < BOT_RESTART_DELAY_TICKS - 1; i += 1) {
      game = advanceBotGame(game);
      expect(game.state.status).toBe('game-over');
    }

    game = advanceBotGame(game);
    expect(game.state.status).toBe('running');
    expect(game.state.score).toBe(0);
  });

  it('is fully deterministic: replaying the same seed for N ticks yields identical trajectories', () => {
    function run(seed: number, ticks: number) {
      let game = createBotGame(seed);
      const trail: string[] = [];
      for (let i = 0; i < ticks; i += 1) {
        game = advanceBotGame(game);
        trail.push(JSON.stringify(game.state.snake));
      }
      return trail;
    }

    expect(run(123, 200)).toEqual(run(123, 200));
  });
});
