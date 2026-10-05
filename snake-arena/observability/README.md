# Local observability stack

A self-hosted OpenTelemetry pipeline for running Snake Arena locally,
as its own Docker Compose project (`snake-arena-observability`),
separate from the application stack in `../docker-compose.yml`.

```
app ──OTLP──▶ OpenTelemetry Collector ──▶ Tempo       traces
                                       ├─▶ Prometheus  metrics
                                       └─▶ Loki        logs
                       Grafana ◀── queries all three
```

| Service        | Image                                         | Host port (override)              |
|----------------|-----------------------------------------------|-----------------------------------|
| otel-collector | `otel/opentelemetry-collector-contrib:0.162.0` | 4317 gRPC, 4318 HTTP (`OTLP_GRPC_PORT`, `OTLP_HTTP_PORT`) |
| tempo          | `grafana/tempo:3.1.0`                         | internal only                     |
| prometheus     | `prom/prometheus:v3.15.0`                     | 9090 (`PROMETHEUS_PORT`)          |
| loki           | `grafana/loki:3.7.8`                          | internal only                     |
| grafana        | `grafana/grafana:13.2.3`                      | 3000 (`GRAFANA_PORT`)             |

Published ports bind to `127.0.0.1` only. Data lives in named volumes
and survives restarts.

## Run it

```bash
cd observability
docker compose up -d                 # GRAFANA_PORT=3001 docker compose up -d if 3000 is taken
```

Open Grafana at http://localhost:3000 and log in as `admin` / `admin`
(set `GRAFANA_ADMIN_PASSWORD` to change it). Prometheus, Tempo and Loki
are already set up as data sources, and the **Snake Arena - Games**
dashboard is preloaded (Dashboards → snake-arena).

### Send the app's telemetry here

**App in Docker Compose:** from `snake-arena/`, add the overlay, which
joins the app to this stack's network and points it at the collector:

```bash
docker compose -f docker-compose.yml -f observability/compose.app.yml up --build
```

**App run directly** (from `backend/`):

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 uv run uvicorn app.main:app --reload
```

Without either, the app exports nothing, as before.

## What you get

- **Traces** in Tempo: one per request, with a span per database query.
  Explore → Tempo → `{resource.service.name="snake-arena"}`.
- **Metrics** in Prometheus: `http_server_duration_milliseconds_*`,
  request/response sizes, active requests, DB connection pool. Labels:
  `job` (service name), `deployment_environment_name`, `service_version`
  (promoted in `prometheus/prometheus.yml`).
- **Game metrics** in Prometheus: `snake_arena_games_created_total`,
  `snake_arena_games_creation_failures_total` (by `error_type`) and
  `snake_arena_games_active`, by `game_mode`, environment and version.
  See *Game metrics* in `../_docs/deployment.md`.
- **Logs** in Loki: the app's and uvicorn's logs, e.g. access logs.
  Explore → Loki → `{service_name="snake-arena"}`.

Signals are linked: a log line logged during a request carries its
`trace_id` (Loki → *TraceID* link opens the trace), and a span in Tempo
links to the logs from the same trace.

`service_version` is only set for images built by CI. Local builds
report no version.

## Games dashboard

`grafana/provisioning/dashboards/snake-arena-games.json`:

- **Filters:** *Environment* and *Version* (multi-select, *All* by
  default). The version list only offers versions seen in the selected
  environments. *Data source* picks the Prometheus to read from.
- **Stats** for the selected time range: active games now, games
  created, creation failures, failure rate.
- **Graphs:** active games by mode, active games by environment and
  version (to compare a new release with the previous one), games
  created per minute by mode, creation failures by `error_type`.

To use it in Grafana Cloud: **Dashboards → New → Import**, upload the
JSON, then pick the stack's Prometheus data source in *Data source*.

## Alerts

`prometheus/rules/snake-arena-alerts.yml` is loaded by Prometheus:

- **GameCreationFailing** (critical): at least 20% of game starts, and
  at least 3, failed over 10 minutes, for 5 minutes, per environment and
  version. Labels: `service`, `environment`, `version`, `owner`,
  `severity`. Annotations: `summary`, `description`, `dashboard_url`
  (the games dashboard filtered to that environment and version),
  `runbook_url` (`../_docs/runbooks/game-creation-failing.md`).

Firing alerts: http://localhost:9090/alerts, or
`GET /api/v1/alerts`, which the on-call poller
(`../on-call-engineer/`) reads. There's no Alertmanager in this stack,
so nothing sends notifications; the poller is the consumer.

Test the rule after changing it:

```bash
cd prometheus/rules
docker run --rm -v "$PWD:/rules" -w /rules --entrypoint promtool \
  prom/prometheus:v3.15.0 test rules snake-arena-alerts.test.yml
```

For the deployed environments, upload the same rules to Grafana Cloud
with `grafana-cloud/apply-alert-rules.sh` (it swaps the dashboard links
to the Grafana Cloud URL).

## Files

| Path                                   | What it configures                       |
|----------------------------------------|------------------------------------------|
| `docker-compose.yml`                   | The five services, ports, volumes, network |
| `compose.app.yml`                      | Overlay connecting the app stack          |
| `otel-collector/config.yaml`           | OTLP in; batching; export per signal      |
| `tempo/tempo.yaml`                     | Single-process Tempo, local storage       |
| `prometheus/prometheus.yml`            | OTLP receiver, promoted labels, rule files |
| `prometheus/rules/`                    | Alerting rules and their promtool tests   |
| `grafana-cloud/apply-alert-rules.sh`   | Uploads the rules to Grafana Cloud        |
| `loki/loki.yaml`                       | Single-process Loki, filesystem storage   |
| `grafana/provisioning/datasources/`    | Data sources and the links between them   |
| `grafana/provisioning/dashboards/`     | Dashboards loaded on startup (the games dashboard; add more JSON here) |

## Stop it

```bash
docker compose down        # keep data
docker compose down -v     # also delete all stored telemetry
```

This stack is for local use. The deployed Render services send to
Grafana Cloud instead (see `../_docs/deployment.md`).
