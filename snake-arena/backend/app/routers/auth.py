from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import CurrentSession, get_current_session, get_optional_user, hash_password, verify_password
from app.models import AuthResponse, BackendError, BackendErrorCode, LoginInput, SignupInput, User
from app.store import UserRecord, store

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_user(record: UserRecord) -> User:
    return User(id=record.id, username=record.username)


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(input: SignupInput) -> AuthResponse:
    username = input.username.strip()
    if store.find_user_by_username(username) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=BackendError(
                code=BackendErrorCode.USERNAME_TAKEN,
                message=f'Username "{username}" is already taken.',
            ).model_dump(),
        )

    record = store.create_user(username, hash_password(input.password))
    token = store.issue_token(record.id)
    return AuthResponse(user=_to_user(record), token=token)


@router.post("/login", response_model=AuthResponse)
async def login(input: LoginInput) -> AuthResponse:
    username = input.username.strip()
    record = store.find_user_by_username(username)
    if record is None or not verify_password(input.password, record.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=BackendError(
                code=BackendErrorCode.INVALID_CREDENTIALS,
                message="Invalid username or password.",
            ).model_dump(),
        )

    token = store.issue_token(record.id)
    return AuthResponse(user=_to_user(record), token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(session: CurrentSession = Depends(get_current_session)) -> None:
    store.revoke_token(session.token)


@router.get("/me", response_model=User | None)
async def get_me(user: UserRecord | None = Depends(get_optional_user)) -> User | None:
    return _to_user(user) if user is not None else None
