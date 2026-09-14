from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.models import LeaderboardEntry, SubmitScoreInput
from app.store import UserRecord, store

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("", response_model=list[LeaderboardEntry])
async def get_leaderboard() -> list[LeaderboardEntry]:
    return store.get_leaderboard()


@router.post("", response_model=list[LeaderboardEntry])
async def submit_score(
    input: SubmitScoreInput, user: UserRecord = Depends(get_current_user)
) -> list[LeaderboardEntry]:
    # `input.username` is client-supplied and untrusted (see openapi.yaml);
    # the authenticated session's username is the one actually recorded.
    return store.submit_score(user.username, input.score, input.mode)
