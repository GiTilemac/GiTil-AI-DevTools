"""Snake engine and bot AI.

A direct port of the frontend's `src/game/{engine,bot,food,rng}.ts`, kept
behaviorally identical (including the seeded mulberry32 RNG) so the
`/watch/live` feed looks like the same simulation the frontend already
implements. Only the bot ever runs server-side; there is no real
multiplayer game loop here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from app.models import BoardSize, Direction, GameMode, GameState, GameStatus, Point

BOARD_WIDTH = 20
BOARD_HEIGHT = 20
INITIAL_SNAKE_LENGTH = 3
TICK_INTERVAL_MS = 150
SCORE_PER_FOOD = 10
BOT_RESTART_DELAY_TICKS = 10

Rng = Callable[[], float]

_MASK32 = 0xFFFFFFFF

_OPPOSITE: dict[Direction, Direction] = {
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
}

_DELTA: dict[Direction, Point] = {
    Direction.UP: Point(x=0, y=-1),
    Direction.DOWN: Point(x=0, y=1),
    Direction.LEFT: Point(x=-1, y=0),
    Direction.RIGHT: Point(x=1, y=0),
}

_ALL_DIRECTIONS = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]


def create_rng(seed: int) -> Rng:
    """mulberry32 — bit-identical to the frontend's `rng.ts`."""
    state = seed & _MASK32

    def next_val() -> float:
        nonlocal state
        state = (state + 0x6D2B79F5) & _MASK32
        t = ((state ^ (state >> 15)) * (1 | state)) & _MASK32
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & _MASK32)) & _MASK32) ^ t
        return ((t ^ (t >> 14)) & _MASK32) / 4294967296

    return next_val


def _is_occupied(point: Point, occupied: list[Point]) -> bool:
    return any(p.x == point.x and p.y == point.y for p in occupied)


def place_food(occupied: list[Point], board: BoardSize, rng: Rng) -> Point:
    max_attempts = 100
    for _ in range(max_attempts):
        candidate = Point(x=int(rng() * board.width), y=int(rng() * board.height))
        if not _is_occupied(candidate, occupied):
            return candidate

    free_cells = [
        Point(x=x, y=y)
        for y in range(board.height)
        for x in range(board.width)
        if not _is_occupied(Point(x=x, y=y), occupied)
    ]
    if not free_cells:
        raise RuntimeError("place_food: no free cells remain on the board")
    index = int(rng() * len(free_cells)) % len(free_cells)
    return free_cells[index]


def is_collision(point: Point, body: list[Point]) -> bool:
    return any(s.x == point.x and s.y == point.y for s in body)


def next_head_position(
    head: Point, direction: Direction, board: BoardSize, mode: GameMode
) -> Point | Literal["DEAD"]:
    delta = _DELTA[direction]
    raw = Point(x=head.x + delta.x, y=head.y + delta.y)
    out_of_bounds = raw.x < 0 or raw.x >= board.width or raw.y < 0 or raw.y >= board.height

    if not out_of_bounds:
        return raw
    if mode == GameMode.WALLS:
        return "DEAD"
    return Point(x=(raw.x + board.width) % board.width, y=(raw.y + board.height) % board.height)


def create_initial_state(mode: GameMode, rng: Rng, board: BoardSize | None = None) -> GameState:
    board = board or BoardSize(width=BOARD_WIDTH, height=BOARD_HEIGHT)
    start_y = board.height // 2
    start_x = board.width // 2

    snake = [Point(x=start_x - i, y=start_y) for i in range(INITIAL_SNAKE_LENGTH)]
    food = place_food(snake, board, rng)

    return GameState(
        board=board,
        mode=mode,
        snake=snake,
        direction=Direction.RIGHT,
        pendingDirection=None,
        food=food,
        score=0,
        status=GameStatus.IDLE,
        tickCount=0,
    )


def set_direction(state: GameState, direction: Direction) -> GameState:
    if state.status == GameStatus.GAME_OVER:
        return state

    current = state.pending_direction or state.direction
    if len(state.snake) > 1 and direction == _OPPOSITE[current]:
        return state

    return state.model_copy(update={"pending_direction": direction})


def step(state: GameState, rng: Rng) -> GameState:
    if state.status == GameStatus.GAME_OVER:
        return state

    direction = state.pending_direction or state.direction
    head = state.snake[0]
    next_head = next_head_position(head, direction, state.board, state.mode)

    if next_head == "DEAD":
        return state.model_copy(
            update={"direction": direction, "pending_direction": None, "status": GameStatus.GAME_OVER}
        )

    ate_food = next_head.x == state.food.x and next_head.y == state.food.y
    body_to_check = state.snake if ate_food else state.snake[:-1]

    if is_collision(next_head, body_to_check):
        return state.model_copy(
            update={"direction": direction, "pending_direction": None, "status": GameStatus.GAME_OVER}
        )

    new_snake = [next_head, *(state.snake if ate_food else state.snake[:-1])]
    new_food = place_food(new_snake, state.board, rng) if ate_food else state.food
    new_score = state.score + SCORE_PER_FOOD if ate_food else state.score

    return state.model_copy(
        update={
            "snake": new_snake,
            "food": new_food,
            "score": new_score,
            "direction": direction,
            "pending_direction": None,
            "status": GameStatus.RUNNING,
            "tick_count": state.tick_count + 1,
        }
    )


@dataclass
class BotGame:
    state: GameState
    rng: Rng
    restart_countdown: int | None = None


def decide_direction(state: GameState) -> Direction:
    head = state.snake[0]
    body = state.snake[:-1]

    def is_safe(direction: Direction) -> bool:
        if len(state.snake) > 1 and direction == _OPPOSITE[state.direction]:
            return False
        nxt = next_head_position(head, direction, state.board, state.mode)
        return nxt != "DEAD" and not any(s.x == nxt.x and s.y == nxt.y for s in body)

    candidates = [d for d in _ALL_DIRECTIONS if is_safe(d)]
    if not candidates:
        return state.direction

    def distance(direction: Direction) -> float:
        nxt = next_head_position(head, direction, state.board, state.mode)
        if nxt == "DEAD":
            return float("inf")
        return abs(nxt.x - state.food.x) + abs(nxt.y - state.food.y)

    candidates.sort(key=distance)
    return candidates[0]


def create_bot_game(seed: int) -> BotGame:
    rng = create_rng(seed)
    state = create_initial_state(GameMode.PASS_THROUGH, rng)
    return BotGame(state=state.model_copy(update={"status": GameStatus.RUNNING}), rng=rng)


def advance_bot_game(game: BotGame) -> BotGame:
    if game.state.status == GameStatus.GAME_OVER:
        remaining = (game.restart_countdown if game.restart_countdown is not None else BOT_RESTART_DELAY_TICKS) - 1
        if remaining <= 0:
            fresh = create_initial_state(game.state.mode, game.rng)
            return BotGame(state=fresh.model_copy(update={"status": GameStatus.RUNNING}), rng=game.rng)
        return BotGame(state=game.state, rng=game.rng, restart_countdown=remaining)

    direction = decide_direction(game.state)
    directed = set_direction(game.state, direction)
    next_state = step(directed, game.rng)
    return BotGame(state=next_state, rng=game.rng)
