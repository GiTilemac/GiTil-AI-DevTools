from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class GameMode(str, Enum):
    PASS_THROUGH = "pass-through"
    WALLS = "walls"


class Direction(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class GameStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    GAME_OVER = "game-over"


class Point(BaseModel):
    x: int
    y: int


class BoardSize(BaseModel):
    width: int
    height: int


class GameState(BaseModel):
    board: BoardSize
    mode: GameMode
    snake: list[Point]
    direction: Direction
    pending_direction: Direction | None = Field(alias="pendingDirection")
    food: Point
    score: int
    status: GameStatus
    tick_count: int = Field(alias="tickCount")

    model_config = {"populate_by_name": True}


class User(BaseModel):
    id: str
    username: str


class AuthResponse(BaseModel):
    user: User
    token: str


class SignupInput(BaseModel):
    username: str
    password: str


class LoginInput(BaseModel):
    username: str
    password: str


class LeaderboardEntry(BaseModel):
    id: str
    username: str
    score: int
    mode: GameMode
    achieved_at: datetime = Field(alias="achievedAt")

    model_config = {"populate_by_name": True, "from_attributes": True}


class SubmitScoreInput(BaseModel):
    username: str
    score: int
    mode: GameMode


class BackendErrorCode(str, Enum):
    USERNAME_TAKEN = "USERNAME_TAKEN"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"


class BackendError(BaseModel):
    code: BackendErrorCode
    message: str
