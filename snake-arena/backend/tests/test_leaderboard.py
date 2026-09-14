from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_leaderboard_is_seeded_and_sorted_descending(client: TestClient) -> None:
    response = client.get("/leaderboard")
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 7
    scores = [e["score"] for e in entries]
    assert scores == sorted(scores, reverse=True)


def test_submit_score_requires_authentication(client: TestClient) -> None:
    response = client.post("/leaderboard", json={"username": "Ghost", "score": 999, "mode": "walls"})
    assert response.status_code == 401


def test_submit_score_appends_and_resorts(client: TestClient, auth_headers: dict) -> None:
    response = client.post(
        "/leaderboard",
        json={"username": "TestPlayer", "score": 1000, "mode": "walls"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 8
    assert entries[0]["score"] == 1000
    assert entries[0]["username"] == "TestPlayer"

    scores = [e["score"] for e in entries]
    assert scores == sorted(scores, reverse=True)


def test_submit_score_uses_the_authenticated_username_not_the_body(
    client: TestClient, auth_headers: dict
) -> None:
    response = client.post(
        "/leaderboard",
        json={"username": "SomeoneElse", "score": 50, "mode": "pass-through"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    new_entry = next(e for e in response.json() if e["score"] == 50)
    assert new_entry["username"] == "TestPlayer"
