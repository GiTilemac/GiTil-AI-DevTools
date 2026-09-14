from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store import Store, store


@pytest.fixture(autouse=True)
def fresh_store() -> Store:
    """Every test starts from a freshly-seeded store, so tests can't leak
    state (users, tokens, leaderboard entries) into each other."""
    store.reset()
    return store


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def signed_up_user(client: TestClient) -> dict:
    response = client.post("/auth/signup", json={"username": "TestPlayer", "password": "s3cret!"})
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def auth_headers(signed_up_user: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {signed_up_user['token']}"}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
