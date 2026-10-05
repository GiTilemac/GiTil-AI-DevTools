"""In-progress game sessions, and the game metrics derived from them.

Games run in the browser; the backend only tracks their lifecycle (see
app/routers/games.py): the frontend starts a session when a game
begins, sends a heartbeat while it runs, and ends it on game over. A
session that stops sending heartbeats (closed tab, lost connection)
expires after SESSION_TIMEOUT_SECONDS.

Sessions are in memory, like the /watch bot game: they're runtime
state, not user data, and a restart just drops the in-progress ones.

Metrics (meter `snake-arena`), each data point tagged with
`deployment.environment.name` and `service.version` (see
app/telemetry.py) plus `game.mode` where known:

- `snake_arena.games.created` (counter): sessions started.
- `snake_arena.games.creation_failures` (counter, + `error.type`):
  starts that were rejected - `invalid_mode`, `too_many_games` - or
  failed unexpectedly (the exception's class name).
- `snake_arena.games.active` (gauge): sessions currently in progress.
"""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone

from opentelemetry import metrics
from opentelemetry.metrics import CallbackOptions, Meter, Observation

from app.models import GameMode
from app.telemetry import deployment_attributes

SESSION_TIMEOUT_SECONDS = 120.0
# The start endpoint is unauthenticated, so cap how many sessions can
# be held in memory at once.
MAX_ACTIVE_SESSIONS = 10_000


class TooManyGamesError(Exception):
    pass


@dataclass
class Session:
    id: str
    mode: GameMode
    user_id: str | None
    started_at: datetime
    last_seen: float


class GameSessions:
    def __init__(
        self,
        meter: Meter,
        *,
        clock: Callable[[], float] = time.monotonic,
        timeout_seconds: float = SESSION_TIMEOUT_SECONDS,
        max_active: int = MAX_ACTIVE_SESSIONS,
    ) -> None:
        self._clock = clock
        self._timeout = timeout_seconds
        self._max_active = max_active
        self._lock = threading.Lock()
        self._sessions: dict[str, Session] = {}

        self._created = meter.create_counter(
            "snake_arena.games.created", unit="{game}", description="Games started."
        )
        self._failures = meter.create_counter(
            "snake_arena.games.creation_failures",
            unit="{failure}",
            description="Game starts that were rejected or failed.",
        )
        meter.create_observable_gauge(
            "snake_arena.games.active",
            callbacks=[self._observe_active],
            unit="{game}",
            description="Games currently in progress.",
        )

    def start(self, mode: GameMode, user_id: str | None) -> Session:
        now = self._clock()
        with self._lock:
            self._expire(now)
            if len(self._sessions) >= self._max_active:
                raise TooManyGamesError
            session = Session(
                id=f"game-{secrets.token_hex(8)}",
                mode=mode,
                user_id=user_id,
                started_at=datetime.now(timezone.utc),
                last_seen=now,
            )
            self._sessions[session.id] = session
        self._created.add(1, {**deployment_attributes(), "game.mode": mode.value})
        return session

    def record_failure(self, error_type: str, mode: GameMode | None = None) -> None:
        attributes = {**deployment_attributes(), "error.type": error_type}
        if mode is not None:
            attributes["game.mode"] = mode.value
        self._failures.add(1, attributes)

    def heartbeat(self, session_id: str) -> bool:
        now = self._clock()
        with self._lock:
            self._expire(now)
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.last_seen = now
            return True

    def end(self, session_id: str) -> bool:
        with self._lock:
            self._expire(self._clock())
            return self._sessions.pop(session_id, None) is not None

    def active_by_mode(self) -> dict[GameMode, int]:
        with self._lock:
            self._expire(self._clock())
            counts = {mode: 0 for mode in GameMode}
            for session in self._sessions.values():
                counts[session.mode] += 1
            return counts

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()

    def _expire(self, now: float) -> None:
        stale = [sid for sid, s in self._sessions.items() if now - s.last_seen > self._timeout]
        for sid in stale:
            del self._sessions[sid]

    def _observe_active(self, _options: CallbackOptions) -> Iterable[Observation]:
        # One point per mode, zeros included, so the series don't
        # disappear while nobody is playing.
        common = deployment_attributes()
        return [
            Observation(count, {**common, "game.mode": mode.value})
            for mode, count in self.active_by_mode().items()
        ]


# Obtained before setup_telemetry() installs the real meter provider;
# OpenTelemetry's proxy meter forwards to it once it's set.
sessions = GameSessions(metrics.get_meter("snake-arena"))
