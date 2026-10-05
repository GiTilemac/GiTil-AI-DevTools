from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.auth import get_optional_user
from app.db_models import UserORM
from app.games import TooManyGamesError, sessions
from app.models import BackendError, BackendErrorCode, GameMode, GameSession, StartGameInput

router = APIRouter(prefix="/games", tags=["games"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown or expired game")


@router.post("", response_model=GameSession, status_code=status.HTTP_201_CREATED)
def start_game(
    input: StartGameInput | None = Body(default=None),
    user: UserORM | None = Depends(get_optional_user),
) -> GameSession:
    try:
        mode = GameMode((input or StartGameInput()).mode)
    except ValueError:
        sessions.record_failure("invalid_mode")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=BackendError(
                code=BackendErrorCode.INVALID_MODE,
                message=f"mode must be one of: {', '.join(m.value for m in GameMode)}.",
            ).model_dump(),
        )

    try:
        session = sessions.start(mode, user.id if user else None)
    except TooManyGamesError:
        sessions.record_failure("too_many_games", mode)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=BackendError(
                code=BackendErrorCode.TOO_MANY_GAMES,
                message="Too many games in progress; try again shortly.",
            ).model_dump(),
        )
    except Exception as exc:
        sessions.record_failure(type(exc).__name__, mode)
        raise

    return GameSession(id=session.id, mode=session.mode, started_at=session.started_at)


@router.post("/{game_id}/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
def heartbeat(game_id: str) -> None:
    if not sessions.heartbeat(game_id):
        raise _not_found()


@router.post("/{game_id}/end", status_code=status.HTTP_204_NO_CONTENT)
def end_game(game_id: str) -> None:
    if not sessions.end(game_id):
        raise _not_found()
