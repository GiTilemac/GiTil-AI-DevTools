from __future__ import annotations

from fastapi.testclient import TestClient

from app.store import Store


def test_signup_returns_user_and_token(client: TestClient) -> None:
    response = client.post("/auth/signup", json={"username": "PixelViper2", "password": "s3cret!"})
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["username"] == "PixelViper2"
    assert body["user"]["id"]
    assert body["token"]


def test_signup_hashes_the_password(client: TestClient, fresh_store: Store) -> None:
    client.post("/auth/signup", json={"username": "PixelViper2", "password": "s3cret!"})
    record = fresh_store.find_user_by_username("PixelViper2")
    assert record is not None
    assert record.password_hash != "s3cret!"
    assert record.password_hash.startswith("$2b$")


def test_signup_rejects_duplicate_username_case_insensitive(client: TestClient, signed_up_user: dict) -> None:
    response = client.post("/auth/signup", json={"username": "testplayer", "password": "whatever"})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "USERNAME_TAKEN"


def test_login_with_correct_credentials(client: TestClient, signed_up_user: dict) -> None:
    response = client.post("/auth/login", json={"username": "TestPlayer", "password": "s3cret!"})
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"] == signed_up_user["user"]["id"]
    assert body["token"]


def test_login_with_wrong_password(client: TestClient, signed_up_user: dict) -> None:
    response = client.post("/auth/login", json={"username": "TestPlayer", "password": "wrong"})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_login_with_unknown_username(client: TestClient) -> None:
    response = client.post("/auth/login", json={"username": "NoSuchUser", "password": "whatever"})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_me_without_token_returns_null(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 200
    assert response.json() is None


def test_me_with_invalid_token_returns_null_not_error(client: TestClient) -> None:
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 200
    assert response.json() is None


def test_me_with_valid_token_returns_user(client: TestClient, auth_headers: dict) -> None:
    response = client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "TestPlayer"


def test_logout_revokes_the_token(client: TestClient, auth_headers: dict) -> None:
    response = client.post("/auth/logout", headers=auth_headers)
    assert response.status_code == 204

    response = client.get("/auth/me", headers=auth_headers)
    assert response.json() is None


def test_logout_without_a_token_is_unauthorized(client: TestClient) -> None:
    response = client.post("/auth/logout")
    assert response.status_code == 401
