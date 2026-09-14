"""In-memory data store, seeded on import. Nothing here persists across a
process restart — this stands in for a real database, mirroring the
frontend mock's `mockDb.ts` (including its seed leaderboard).
"""

from __future__ import annotations

import asyncio
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.game import TICK_INTERVAL_MS, BotGame, advance_bot_game, create_bot_game
from app.models import GameMode, GameState, LeaderboardEntry


@dataclass
class UserRecord:
    id: str
    username: str
    password_hash: str


def _next_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(4)}"


def _seed_leaderboard() -> list[LeaderboardEntry]:
    entries = [
        LeaderboardEntry(id="seed-1", username="PixelViper", score=480, mode=GameMode.WALLS, achievedAt=datetime(2026, 9, 1, 10, tzinfo=timezone.utc)),
        LeaderboardEntry(id="seed-2", username="GridMaster", score=410, mode=GameMode.PASS_THROUGH, achievedAt=datetime(2026, 9, 2, 10, tzinfo=timezone.utc)),
        LeaderboardEntry(id="seed-3", username="LoopHound", score=360, mode=GameMode.PASS_THROUGH, achievedAt=datetime(2026, 9, 3, 10, tzinfo=timezone.utc)),
        LeaderboardEntry(id="seed-4", username="ByteCoil", score=300, mode=GameMode.WALLS, achievedAt=datetime(2026, 9, 4, 10, tzinfo=timezone.utc)),
        LeaderboardEntry(id="seed-5", username="TailWhip", score=250, mode=GameMode.WALLS, achievedAt=datetime(2026, 9, 5, 10, tzinfo=timezone.utc)),
        LeaderboardEntry(id="seed-6", username="CrunchApple", score=180, mode=GameMode.PASS_THROUGH, achievedAt=datetime(2026, 9, 6, 10, tzinfo=timezone.utc)),
        LeaderboardEntry(id="seed-7", username="SlowSlither", score=90, mode=GameMode.WALLS, achievedAt=datetime(2026, 9, 7, 10, tzinfo=timezone.utc)),
    ]
    return sorted(entries, key=lambda e: e.score, reverse=True)


class Store:
    """Holds all server-side state. One instance per process."""

    def __init__(self) -> None:
        self._watch_lock = asyncio.Lock()
        self.reset()

    def reset(self) -> None:
        """Restores the store to its freshly-seeded state. Used between
        tests for isolation, mirroring the frontend mock's `resetDb`/
        `resetWatchState` helpers."""
        self.users: dict[str, UserRecord] = {}
        self.leaderboard: list[LeaderboardEntry] = _seed_leaderboard()
        self.tokens: dict[str, str] = {}  # token -> user_id

        self._bot_game: BotGame = create_bot_game(seed=int(time.time() * 1000))
        self._last_tick_monotonic: float = time.monotonic()

    # -- users -----------------------------------------------------------

    def find_user_by_username(self, username: str) -> UserRecord | None:
        lowered = username.lower()
        return next((u for u in self.users.values() if u.username.lower() == lowered), None)

    def get_user(self, user_id: str) -> UserRecord | None:
        return self.users.get(user_id)

    def create_user(self, username: str, password_hash: str) -> UserRecord:
        user = UserRecord(id=_next_id("user"), username=username, password_hash=password_hash)
        self.users[user.id] = user
        return user

    # -- tokens ------------------------------------------------------------

    def issue_token(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self.tokens[token] = user_id
        return token

    def resolve_token(self, token: str) -> UserRecord | None:
        user_id = self.tokens.get(token)
        return self.get_user(user_id) if user_id else None

    def revoke_token(self, token: str) -> None:
        self.tokens.pop(token, None)

    # -- leaderboard -------------------------------------------------------

    def get_leaderboard(self) -> list[LeaderboardEntry]:
        return sorted(self.leaderboard, key=lambda e: e.score, reverse=True)

    def submit_score(self, username: str, score: int, mode: GameMode) -> list[LeaderboardEntry]:
        entry = LeaderboardEntry(
            id=_next_id("score"),
            username=username,
            score=score,
            mode=mode,
            achievedAt=datetime.now(timezone.utc),
        )
        self.leaderboard.append(entry)
        self.leaderboard.sort(key=lambda e: e.score, reverse=True)
        return list(self.leaderboard)

    # -- watch/bot -----------------------------------------------------------

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
