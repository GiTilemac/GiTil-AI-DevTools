from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy import text

from app.store import Store
from app.telemetry import build_resource, setup_telemetry


@pytest.fixture(autouse=True)
def telemetry_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # conftest disables the SDK for the rest of the suite; with it
    # disabled, SDK tracers record nothing.
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    for name in ("OTEL_SERVICE_NAME", "DEPLOYMENT_ENVIRONMENT", "APP_VERSION", "OTEL_RESOURCE_ATTRIBUTES"):
        monkeypatch.delenv(name, raising=False)


def test_resource_defaults() -> None:
    attributes = build_resource().attributes
    assert attributes["service.name"] == "snake-arena"
    assert attributes["deployment.environment.name"] == "local"
    assert attributes["deployment.environment"] == "local"
    assert "service.version" not in attributes


def test_resource_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "production")
    monkeypatch.setenv("APP_VERSION", "20261005-120000-abc1234")
    attributes = build_resource().attributes
    assert attributes["service.name"] == "snake-arena"
    assert attributes["deployment.environment.name"] == "production"
    assert attributes["deployment.environment"] == "production"
    assert attributes["service.version"] == "20261005-120000-abc1234"


def test_empty_version_is_omitted(monkeypatch: pytest.MonkeyPatch) -> None:
    # Local `docker build` without --build-arg sets APP_VERSION="".
    monkeypatch.setenv("APP_VERSION", "")
    assert "service.version" not in build_resource().attributes


Instrumented = tuple[TestClient, InMemorySpanExporter, InMemoryLogRecordExporter]


@pytest.fixture
def instrumented(monkeypatch: pytest.MonkeyPatch) -> Iterator[Instrumented]:
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "dev")
    monkeypatch.setenv("APP_VERSION", "20261005-120000-abc1234")

    store = Store(database_url="sqlite://")
    app = FastAPI()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/count")
    def count() -> dict[str, int]:
        logging.getLogger("app.test").warning("counting")
        with store.engine.connect() as conn:
            return {"n": conn.execute(text("SELECT 1")).scalar_one()}

    exporter = InMemorySpanExporter()
    log_exporter = InMemoryLogRecordExporter()
    setup_telemetry(
        app,
        store.engine,
        span_processor=SimpleSpanProcessor(exporter),
        log_processor=SimpleLogRecordProcessor(log_exporter),
        set_global=False,
    )
    try:
        yield TestClient(app), exporter, log_exporter
    finally:
        FastAPIInstrumentor.uninstrument_app(app)
        SQLAlchemyInstrumentor().uninstrument()
        for name in ("", "uvicorn", "uvicorn.access"):
            log = logging.getLogger(name)
            for handler in [h for h in log.handlers if isinstance(h, LoggingHandler)]:
                log.removeHandler(handler)


def test_requests_and_queries_are_traced_with_resource(instrumented: Instrumented) -> None:
    client, exporter, _ = instrumented
    assert client.get("/count").json() == {"n": 1}

    spans = exporter.get_finished_spans()
    server = [s for s in spans if s.attributes.get("http.route") == "/count"]
    queries = [s for s in spans if s.attributes.get("db.system") == "sqlite"]
    assert server, [s.name for s in spans]
    assert queries, [s.name for s in spans]

    for span in server + queries:
        assert span.resource.attributes["service.name"] == "snake-arena"
        assert span.resource.attributes["deployment.environment.name"] == "dev"
        assert span.resource.attributes["service.version"] == "20261005-120000-abc1234"


def test_health_checks_are_not_traced(instrumented: Instrumented) -> None:
    client, exporter, _ = instrumented
    client.get("/health")
    assert not [s for s in exporter.get_finished_spans() if s.attributes.get("http.route") == "/health"]


def test_logs_are_exported_with_resource_and_trace(instrumented: Instrumented) -> None:
    client, exporter, log_exporter = instrumented
    client.get("/count")

    records = [r for r in log_exporter.get_finished_logs() if r.log_record.body == "counting"]
    assert records
    record = records[0]
    assert record.resource.attributes["deployment.environment.name"] == "dev"
    assert record.resource.attributes["service.version"] == "20261005-120000-abc1234"
    # Logged inside the request, so it carries that request's trace.
    server = next(s for s in exporter.get_finished_spans() if s.attributes.get("http.route") == "/count")
    assert record.log_record.trace_id == server.context.trace_id
