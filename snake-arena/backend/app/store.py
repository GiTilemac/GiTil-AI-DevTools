"""Persistent store, backed by a SQL database via SQLAlchemy (see
app/db.py) - DATABASE_URL picks the backend, defaulting to a local
SQLite file. The bot/watch simulation is unrelated, ephemeral runtime
state (not user data), so it stays in-memory here regardless of
DATABASE_URL.
"""

from __future__ import annotations

import asyncio
import secrets
import time
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db import Base, database_url_from_env, make_engine, make_session_factory
from app.db_models import LeaderboardEntryORM, TokenORM, UserORM
from app.game import TICK_INTERVAL_MS, BotGame, advance_bot_game, create_bot_game
from app.models import GameMode, GameState


def _next_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4)}"


class UsernameTakenError(Exception):
    """Raised by create_user on a duplicate username. The router already
    pre-checks for this, so in practice this only fires on the race
    between two concurrent signups for the same name - the database's
    own unique constraint is the actual source of truth."""


_SEED_LEADERBOARD = [
    ("seed-1", "PixelViper", 480, GameMode.WALLS, datetime(2026, 9, 1, 10, tzinfo=timezone.utc)),
    ("seed-2", "GridMaster", 410, GameMode.PASS_THROUGH, datetime(2026, 9, 2, 10, tzinfo=timezone.utc)),
    ("seed-3", "LoopHound", 360, GameMode.PASS_THROUGH, datetime(2026, 9, 3, 10, tzinfo=timezone.utc)),
    ("seed-4", "ByteCoil", 300, GameMode.WALLS, datetime(2026, 9, 4, 10, tzinfo=timezone.utc)),
    ("seed-5", "TailWhip", 250, GameMode.WALLS, datetime(2026, 9, 5, 10, tzinfo=timezone.utc)),
    ("seed-6", "CrunchApple", 180, GameMode.PASS_THROUGH, datetime(2026, 9, 6, 10, tzinfo=timezone.utc)),
    ("seed-7", "SlowSlither", 90, GameMode.WALLS, datetime(2026, 9, 7, 10, tzinfo=timezone.utc)),
]


class Store:
    """One instance per process. DB-backed methods (users/tokens/
    leaderboard) are plain sync calls - FastAPI runs sync endpoints in a
    thread pool, so this never blocks the event loop that drives
    /watch/live. `tick_watch` is the one exception: it's async because it
    coordinates with the async SSE endpoint via an asyncio.Lock.
    """

    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or database_url_from_env()
        self._engine = make_engine(self._database_url)
        self._session_factory = make_session_factory(self._engine)
        self._init_schema()

        self._watch_lock = asyncio.Lock()
        self._bot_game: BotGame = create_bot_game(seed=int(time.time() * 1000))
        self._last_tick_monotonic: float = time.monotonic()

    def _init_schema(self) -> None:
        Base.metadata.create_all(self._engine)
        with self._session_factory() as session:
            already_seeded = session.scalar(select(func.count()).select_from(LeaderboardEntryORM))
            if not already_seeded:
                session.add_all(
                    LeaderboardEntryORM(
                        id=id_, username=username, score=score, mode=mode.value, achieved_at=achieved_at
                    )
                    for id_, username, score, mode, achieved_at in _SEED_LEADERBOARD
                )
                session.commit()

    def reset(self) -> None:
        """Drops and recreates all tables, then re-seeds, and resets the
        bot/watch state. Used between tests for isolation."""
        Base.metadata.drop_all(self._engine)
        self._init_schema()

        self._bot_game = create_bot_game(seed=int(time.time() * 1000))
        self._last_tick_monotonic = time.monotonic()

    # -- users --------------------------------------------------------------

    def find_user_by_username(self, username: str) -> UserORM | None:
        with self._session_factory() as session:
            return session.scalar(select(UserORM).where(func.lower(UserORM.username) == username.lower()))

    def get_user(self, user_id: str) -> UserORM | None:
        with self._session_factory() as session:
            return session.get(UserORM, user_id)

    def create_user(self, username: str, password_hash: str) -> UserORM:
        user = UserORM(id=_next_id("user"), username=username, password_hash=password_hash)
        with self._session_factory() as session:
            session.add(user)
            try:
                session.commit()
            except IntegrityError as exc:
                raise UsernameTakenError(username) from exc
        return user

    # -- tokens ---------------------------------------------------------------

    def issue_token(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        with self._session_factory() as session:
            session.add(TokenORM(token=token, user_id=user_id))
            session.commit()
        return token

    def resolve_token(self, token: str) -> UserORM | None:
        with self._session_factory() as session:
            token_row = session.get(TokenORM, token)
            if token_row is None:
                return None
            return session.get(UserORM, token_row.user_id)

    def revoke_token(self, token: str) -> None:
        with self._session_factory() as session:
            token_row = session.get(TokenORM, token)
            if token_row is not None:
                session.delete(token_row)
                session.commit()

    # -- leaderboard ----------------------------------------------------------

    def get_leaderboard(self) -> list[LeaderboardEntryORM]:
        with self._session_factory() as session:
            return list(
                session.scalars(select(LeaderboardEntryORM).order_by(LeaderboardEntryORM.score.desc()))
            )

    def submit_score(self, username: str, score: int, mode: GameMode) -> list[LeaderboardEntryORM]:
        entry = LeaderboardEntryORM(
            id=_next_id("score"),
            username=username,
            score=score,
            mode=mode.value,
            achieved_at=datetime.now(timezone.utc),
        )
        with self._session_factory() as session:
            session.add(entry)
            session.commit()
        return self.get_leaderboard()

    # -- watch/bot: unrelated ephemeral runtime state, not persisted --------

    async def tick_watch(self) -> GameState:
        """Returns the current bot GameState, advancing it at most once per
        TICK_INTERVAL_MS regardless of how many concurrent watchers call
        this — mirrors the frontend's single shared `setInterval` driving
        every subscriber.
        """
        async with self._watch_lock:
            now = time.monotonic()
            if now - self._last_tick_monotonic >= TICK_INTERVAL_MS / 1000:
                self._bot_game = advance_bot_game(self._bot_game)
                self._last_tick_monotonic = now
            return self._bot_game.state


store = Store()
