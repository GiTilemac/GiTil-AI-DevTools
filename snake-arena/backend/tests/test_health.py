from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_health_without_render_commit(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "commit": None}


def test_health_reports_render_commit(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc123")
    response = client.get("/health")
    assert response.json() == {"status": "ok", "commit": "abc123"}
