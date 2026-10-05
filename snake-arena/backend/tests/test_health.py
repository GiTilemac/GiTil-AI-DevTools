from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_health_without_version(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_VERSION", raising=False)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": None}


def test_health_reports_version(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_VERSION", "20261005-120000-abc1234")
    response = client.get("/health")
    assert response.json() == {"status": "ok", "version": "20261005-120000-abc1234"}


def test_health_treats_empty_version_as_none(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # Local `docker build` without --build-arg sets APP_VERSION="".
    monkeypatch.setenv("APP_VERSION", "")
    assert client.get("/health").json()["version"] is None
