"""Black-box smoke tests against a running Snake Arena stack (e.g. the
Docker Compose stack), exercising the real HTTP boundary, the real
Postgres database, and the built frontend's static file serving -
unlike backend/tests, which drive the FastAPI app in-process against an
in-memory SQLite DB. Point BASE_URL at the stack under test; defaults to
the Docker Compose stack's published port.

Run with the backend's own uv-managed venv, which already has pytest
and httpx as dev dependencies:

    cd backend && uv run pytest ../integration-tests
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")


@pytest.fixture
def client() -> httpx.Client:
    # A browser-like Accept header, matching what the backend's SPA
    # fallback (app/main.py) checks for on GET / and other app routes.
    headers = {"Accept": "text/html,application/xhtml+xml"}
    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=10) as client:
        yield client


def test_health(client: httpx.Client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_frontend_is_served(client: httpx.Client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_signup_submit_score_and_leaderboard(client: httpx.Client) -> None:
    username = f"ci-smoke-{uuid.uuid4().hex[:8]}"

    signup = client.post(
        "/auth/signup", json={"username": username, "password": "s3cret-pass!"}
    )
    assert signup.status_code == 201
    token = signup.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    submit = client.post(
        "/leaderboard",
        json={"username": username, "score": 42, "mode": "walls"},
        headers=headers,
    )
    assert submit.status_code == 200

    leaderboard = client.get("/leaderboard")
    assert leaderboard.status_code == 200
    entries = leaderboard.json()
    assert any(e["username"] == username and e["score"] == 42 for e in entries)
