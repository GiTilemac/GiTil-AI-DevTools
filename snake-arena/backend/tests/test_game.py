from __future__ import annotations

from app.game import (
    BoardSize,
    GameMode,
    GameStatus,
    Point,
    create_initial_state,
    create_rng,
    next_head_position,
    step,
)
from app.models import Direction


def test_rng_is_deterministic_for_a_given_seed() -> None:
    a = create_rng(42)
    b = create_rng(42)
    assert [a() for _ in range(5)] == [b() for _ in range(5)]


def test_walls_mode_exiting_the_board_kills_the_snake() -> None:
    board = BoardSize(width=5, height=5)
    head = Point(x=4, y=2)
    assert next_head_position(head, Direction.RIGHT, board, GameMode.WALLS) == "DEAD"


def test_pass_through_mode_wraps_around_the_board() -> None:
    board = BoardSize(width=5, height=5)
    head = Point(x=4, y=2)
    result = next_head_position(head, Direction.RIGHT, board, GameMode.PASS_THROUGH)
    assert result == Point(x=0, y=2)


def test_step_grows_snake_and_scores_on_eating_food() -> None:
    rng = create_rng(1)
    state = create_initial_state(GameMode.PASS_THROUGH, rng, board=BoardSize(width=5, height=5))
    state = state.model_copy(update={"status": GameStatus.RUNNING, "food": Point(x=state.snake[0].x + 1, y=state.snake[0].y)})

    before_length = len(state.snake)
    after = step(state, rng)

    assert after.score == 10
    assert len(after.snake) == before_length + 1
    assert after.snake[0] == Point(x=state.food.x, y=state.food.y)


def test_step_is_a_noop_once_game_over() -> None:
    rng = create_rng(1)
    state = create_initial_state(GameMode.WALLS, rng, board=BoardSize(width=5, height=5))
    state = state.model_copy(update={"status": GameStatus.GAME_OVER})

    assert step(state, rng) == state
