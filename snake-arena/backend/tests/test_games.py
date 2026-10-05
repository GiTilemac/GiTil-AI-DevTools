from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from app.games import GameSessions
from app.main import app
from app.models import GameMode
from app.routers import games as games_router

VERSION = "20261006-120000-abc1234"


# -- API ---------------------------------------------------------------


def test_start_game(client: TestClient) -> None:
    response = client.post("/games", json={"mode": "walls"})
    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("game-")
    assert body["mode"] == "walls"
    assert "startedAt" in body


def test_start_game_as_logged_in_user(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/games", json={"mode": "pass-through"}, headers=auth_headers)
    assert response.status_code == 201


@pytest.mark.parametrize("payload", [{"mode": "sideways"}, {}, None])
def test_start_game_rejects_invalid_mode(client: TestClient, payload: dict[str, str] | None) -> None:
    response = client.post("/games", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_MODE"


def test_heartbeat_and_end(client: TestClient) -> None:
    game_id = client.post("/games", json={"mode": "walls"}).json()["id"]
    assert client.post(f"/games/{game_id}/heartbeat").status_code == 204
    assert client.post(f"/games/{game_id}/end").status_code == 204
    # Ended games are gone.
    assert client.post(f"/games/{game_id}/heartbeat").status_code == 404
    assert client.post(f"/games/{game_id}/end").status_code == 404


def test_unknown_game_is_404(client: TestClient) -> None:
    assert client.post("/games/game-nope/heartbeat").status_code == 404
    assert client.post("/games/game-nope/end").status_code == 404


# -- Metrics -----------------------------------------------------------


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def reader(monkeypatch: pytest.MonkeyPatch) -> InMemoryMetricReader:
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "production")
    monkeypatch.setenv("APP_VERSION", VERSION)
    return InMemoryMetricReader()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def tracked(reader: InMemoryMetricReader, clock: FakeClock) -> GameSessions:
    meter = MeterProvider(metric_readers=[reader]).get_meter("test")
    return GameSessions(meter, clock=clock, timeout_seconds=60, max_active=3)


def points(reader: InMemoryMetricReader, name: str) -> list[tuple[dict[str, str], float]]:
    data = reader.get_metrics_data()
    found = []
    for rm in data.resource_metrics if data else []:
        for sm in rm.scope_metrics:
            for metric in sm.metrics:
                if metric.name == name:
                    found += [(dict(p.attributes), p.value) for p in metric.data.data_points]
    return found


def value(reader: InMemoryMetricReader, name: str, **attributes: str) -> float:
    matching = [
        v for attrs, v in points(reader, name)
        if all(attrs.get(k.replace("_", ".")) == want for k, want in attributes.items())
    ]
    return sum(matching)


def test_games_created_counts_by_mode_with_environment_and_version(
    tracked: GameSessions, reader: InMemoryMetricReader
) -> None:
    tracked.start(GameMode.WALLS, None)
    tracked.start(GameMode.WALLS, "user-1")
    tracked.start(GameMode.PASS_THROUGH, None)

    created = points(reader, "snake_arena.games.created")
    assert {a["game.mode"]: v for a, v in created} == {"walls": 2, "pass-through": 1}
    for attributes, _ in created:
        assert attributes["deployment.environment.name"] == "production"
        assert attributes["service.version"] == VERSION


def test_active_games_follow_start_end_and_expiry(
    tracked: GameSessions, reader: InMemoryMetricReader, clock: FakeClock
) -> None:
    walls = tracked.start(GameMode.WALLS, None)
    idle = tracked.start(GameMode.WALLS, None)
    tracked.start(GameMode.PASS_THROUGH, None)
    assert value(reader, "snake_arena.games.active", game_mode="walls") == 2
    assert value(reader, "snake_arena.games.active", game_mode="pass-through") == 1

    tracked.end(walls.id)
    assert value(reader, "snake_arena.games.active", game_mode="walls") == 1

    # Only one game keeps sending heartbeats; the others expire.
    clock.now += 45
    tracked.heartbeat(idle.id)
    clock.now += 45
    assert value(reader, "snake_arena.games.active", game_mode="walls") == 1
    assert value(reader, "snake_arena.games.active", game_mode="pass-through") == 0

    active = points(reader, "snake_arena.games.active")
    assert {a["game.mode"] for a, _ in active} == {"walls", "pass-through"}
    for attributes, _ in active:
        assert attributes["deployment.environment.name"] == "production"
        assert attributes["service.version"] == VERSION


@pytest.fixture
def api_with_metrics(
    tracked: GameSessions, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setattr(games_router, "sessions", tracked)
    yield TestClient(app, raise_server_exceptions=False)


def test_creation_failures_by_reason(
    api_with_metrics: TestClient, reader: InMemoryMetricReader
) -> None:
    client = api_with_metrics
    assert client.post("/games", json={"mode": "sideways"}).status_code == 422
    for _ in range(3):
        assert client.post("/games", json={"mode": "walls"}).status_code == 201
    response = client.post("/games", json={"mode": "walls"})  # over max_active=3
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "TOO_MANY_GAMES"

    failures = {a["error.type"]: v for a, v in points(reader, "snake_arena.games.creation_failures")}
    assert failures == {"invalid_mode": 1, "too_many_games": 1}
    assert value(reader, "snake_arena.games.created") == 3
    for attributes, _ in points(reader, "snake_arena.games.creation_failures"):
        assert attributes["deployment.environment.name"] == "production"
        assert attributes["service.version"] == VERSION


def test_unexpected_errors_count_as_failures(
    api_with_metrics: TestClient,
    tracked: GameSessions,
    reader: InMemoryMetricReader,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(*_args: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(tracked, "start", broken)
    assert api_with_metrics.post("/games", json={"mode": "walls"}).status_code == 500
    assert points(reader, "snake_arena.games.creation_failures") == [
        ({"deployment.environment.name": "production", "service.version": VERSION,
          "error.type": "RuntimeError", "game.mode": "walls"}, 1)
    ]
