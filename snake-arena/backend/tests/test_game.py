from __future__ import annotations

from app.game import (
    BoardSize,
    GameMode,
    GameStatus,
    Point,
    create_initial_state,
    create_rng,
    next_head_position,
    set_direction,
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


def test_step_ends_the_game_on_self_collision() -> None:
    rng = create_rng(1)
    board = BoardSize(width=10, height=10)
    state = create_initial_state(GameMode.WALLS, rng, board=board)
    # Head at (5,5) moving UP lands on (5,4), which is body segment index 2
    # (not the tail, which moves out of the way) -> must be a collision.
    state = state.model_copy(
        update={
            "snake": [
                Point(x=5, y=5),
                Point(x=9, y=9),
                Point(x=5, y=4),
                Point(x=1, y=1),
                Point(x=0, y=0),
            ],
            "direction": Direction.UP,
            "food": Point(x=8, y=8),
        }
    )

    assert step(state, rng).status == GameStatus.GAME_OVER


def test_set_direction_buffers_a_valid_change() -> None:
    rng = create_rng(1)
    state = create_initial_state(GameMode.WALLS, rng)
    assert set_direction(state, Direction.UP).pending_direction == Direction.UP


def test_set_direction_ignores_an_immediate_180_degree_reversal() -> None:
    rng = create_rng(1)
    state = create_initial_state(GameMode.WALLS, rng)  # facing RIGHT, length 3
    assert set_direction(state, Direction.LEFT).pending_direction is None


def test_set_direction_is_a_noop_once_game_over() -> None:
    rng = create_rng(1)
    state = create_initial_state(GameMode.WALLS, rng).model_copy(update={"status": GameStatus.GAME_OVER})

    assert set_direction(state, Direction.UP) == state
