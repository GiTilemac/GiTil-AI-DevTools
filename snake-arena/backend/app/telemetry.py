"""OpenTelemetry setup: traces and metrics for every HTTP request (FastAPI)
and database query (SQLAlchemy), plus the app's and uvicorn's logs, all
tagged with which service, environment and deployed version produced
them.

Resource attributes, read from the environment:

- `service.name`: `OTEL_SERVICE_NAME`, default `snake-arena`.
- `deployment.environment.name`: `DEPLOYMENT_ENVIRONMENT` (`dev` /
  `production` on Render, see render.yaml), default `local`. Also sent
  as the older `deployment.environment`, which many backends still key
  on.
- `service.version`: `APP_VERSION`, the image tag baked in by CI
  (YYYYMMDD-HHMMSS-shortsha, see ../Dockerfile). Omitted when unset.

Export is OTLP over HTTP, configured with the standard OTEL_EXPORTER_OTLP_*
variables (endpoint, headers). With no endpoint set, telemetry is still
recorded but not exported, so local runs and tests need no collector.
`OTEL_TRACES_EXPORTER=console` prints spans to stdout instead, for
local debugging.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from opentelemetry import _logs, metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LogRecordProcessor
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExporter,
    SpanProcessor,
)
from sqlalchemy import Engine

DEFAULT_SERVICE_NAME = "snake-arena"
DEFAULT_ENVIRONMENT = "local"

# Loggers whose records are exported. uvicorn's own loggers don't
# propagate to the root logger, so they're attached separately.
_EXPORTED_LOGGERS = ("", "uvicorn", "uvicorn.access")


def deployment_attributes() -> dict[str, str]:
    """Environment and deployed version, as OpenTelemetry attributes.
    Part of the resource (so on every signal), and also set directly on
    the app's own metric data points (app/games.py), so they're plain
    labels in every metrics backend, not only those that promote
    resource attributes."""
    attributes = {
        "deployment.environment.name": os.environ.get("DEPLOYMENT_ENVIRONMENT") or DEFAULT_ENVIRONMENT,
    }
    version = os.environ.get("APP_VERSION")
    if version:
        attributes["service.version"] = version
    return attributes


def build_resource() -> Resource:
    attributes = {
        "service.name": os.environ.get("OTEL_SERVICE_NAME") or DEFAULT_SERVICE_NAME,
        **deployment_attributes(),
    }
    attributes["deployment.environment"] = attributes["deployment.environment.name"]
    # Resource.create also merges in OTEL_RESOURCE_ATTRIBUTES; the
    # attributes above take precedence over it.
    return Resource.create(attributes)


def _otlp_configured(signal: str) -> bool:
    return bool(
        os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        or os.environ.get(f"OTEL_EXPORTER_OTLP_{signal}_ENDPOINT")
    )


def _default_span_processor() -> SpanProcessor | None:
    exporter: SpanExporter
    if os.environ.get("OTEL_TRACES_EXPORTER") == "console":
        exporter = ConsoleSpanExporter()
    elif _otlp_configured("TRACES"):
        exporter = OTLPSpanExporter()
    else:
        return None
    return BatchSpanProcessor(exporter)


def _default_metric_reader() -> MetricReader | None:
    if not _otlp_configured("METRICS"):
        return None
    return PeriodicExportingMetricReader(OTLPMetricExporter())


def _default_log_processor() -> LogRecordProcessor | None:
    if not _otlp_configured("LOGS"):
        return None
    return BatchLogRecordProcessor(OTLPLogExporter())


def setup_telemetry(
    app: FastAPI,
    engine: Engine,
    *,
    span_processor: SpanProcessor | None = None,
    metric_reader: MetricReader | None = None,
    log_processor: LogRecordProcessor | None = None,
    set_global: bool = True,
) -> TracerProvider:
    """Instruments `app` and `engine`, and exports Python logging. The
    exporters default to what the environment configures; tests pass
    in-memory processors/readers and `set_global=False` instead, since
    OpenTelemetry's global providers can only be set once per process."""
    resource = build_resource()

    tracer_provider = TracerProvider(resource=resource)
    span_processor = span_processor or _default_span_processor()
    if span_processor is not None:
        tracer_provider.add_span_processor(span_processor)

    metric_reader = metric_reader or _default_metric_reader()
    meter_provider = MeterProvider(
        resource=resource, metric_readers=[metric_reader] if metric_reader else []
    )

    log_processor = log_processor or _default_log_processor()
    logger_provider = LoggerProvider(resource=resource)
    if log_processor is not None:
        logger_provider.add_log_record_processor(log_processor)
        # Records logged inside a request carry its trace and span IDs,
        # so a log line links to its trace.
        handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
        for name in _EXPORTED_LOGGERS:
            logging.getLogger(name).addHandler(handler)

    if set_global:
        trace.set_tracer_provider(tracer_provider)
        metrics.set_meter_provider(meter_provider)
        _logs.set_logger_provider(logger_provider)

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        # Health checks run every few seconds from Render and the deploy
        # workflows; tracing them would drown out real traffic.
        excluded_urls="/health",
    )
    SQLAlchemyInstrumentor().instrument(
        engine=engine, tracer_provider=tracer_provider, meter_provider=meter_provider
    )
    return tracer_provider
