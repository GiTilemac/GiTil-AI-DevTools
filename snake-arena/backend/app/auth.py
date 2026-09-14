"""Password hashing and bearer-token session handling."""

from __future__ import annotations

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.store import UserRecord, store

# auto_error=False so a missing header doesn't 403 before we can decide
# whether the endpoint requires auth (see `get_optional_user`).
_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))


def _resolve(credentials: HTTPAuthorizationCredentials | None) -> UserRecord | None:
    if credentials is None:
        return None
    return store.resolve_token(credentials.credentials)


class CurrentSession:
    """The authenticated user plus the raw token that authenticated them,
    so an endpoint like logout can revoke exactly that token."""

    def __init__(self, user: UserRecord, token: str) -> None:
        self.user = user
        self.token = token


async def get_current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentSession:
    """Dependency for endpoints that require authentication."""
    user = _resolve(credentials)
    if user is None or credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return CurrentSession(user=user, token=credentials.credentials)


async def get_current_user(session: CurrentSession = Depends(get_current_session)) -> UserRecord:
    """Dependency for endpoints that need the authenticated user but not
    the raw token."""
    return session.user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> UserRecord | None:
    """Dependency for endpoints callable by guests, e.g. GET /auth/me."""
    return _resolve(credentials)
