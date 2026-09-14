"""Tests for the bot AI driving /watch/live (spec 3.6), mirroring the
frontend's own game/bot.test.ts coverage for the same behavior - this
module is a direct, verified-deterministic port of that file (see
game.py's docstring and the RNG cross-check against the JS original).
"""

from __future__ import annotations

from app.game import BOT_RESTART_DELAY_TICKS, advance_bot_game, create_bot_game, decide_direction
from app.models import Direction, GameStatus

_OPPOSITE = {
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
}


def test_decide_direction_never_reverses_into_the_neck() -> None:
    game = create_bot_game(seed=1)
    for _ in range(300):
        if game.state.status == GameStatus.RUNNING:
            direction = decide_direction(game.state)
            assert direction != _OPPOSITE[game.state.direction]
        game = advance_bot_game(game)


def test_advance_bot_game_runs_many_ticks_without_error() -> None:
    game = create_bot_game(seed=42)
    for _ in range(500):
        game = advance_bot_game(game)


def test_advance_bot_game_restarts_exactly_after_the_delay() -> None:
    game = create_bot_game(seed=7)
    game.state = game.state.model_copy(update={"status": GameStatus.GAME_OVER})

    for _ in range(BOT_RESTART_DELAY_TICKS - 1):
        game = advance_bot_game(game)
        assert game.state.status == GameStatus.GAME_OVER

    game = advance_bot_game(game)
    assert game.state.status == GameStatus.RUNNING
    assert game.state.score == 0


def test_advance_bot_game_is_deterministic_for_a_given_seed() -> None:
    def run(seed: int, ticks: int) -> list[str]:
        game = create_bot_game(seed)
        trail = []
        for _ in range(ticks):
            game = advance_bot_game(game)
            trail.append(str(game.state.snake))
        return trail

    assert run(123, 200) == run(123, 200)
