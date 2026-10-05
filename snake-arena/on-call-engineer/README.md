# On-call engineer

`poll_alerts.py` polls the alert API every minute. The first time an
alert fires, it hands the alert's details to a headless coding agent
(Claude Code, `claude -p`), which investigates and writes an incident
report.

```
Prometheus / Grafana Cloud ──GET /api/v1/alerts (every 60 s)──▶ poll_alerts.py
                                                                  │ new firing alert
                                                                  ▼
                                              claude -p  (read-only tools, repo as cwd)
                                                                  │
                                                  incidents/<time>-<alert>-<id>/
                                                    alert.json  report.md  agent.log
```

## Run it

Local stack (`../observability/`), default settings:

```bash
python3 poll_alerts.py            # poll forever
python3 poll_alerts.py --once     # one poll, wait for the agent, exit
```

Against Grafana Cloud (the deployed dev and production environments):

```bash
export ALERTS_URL=https://prometheus-prod-<n>-<region>.grafana.net/api/prom/api/v1/alerts
export ALERTS_USER=<Prometheus instance ID>
export ALERTS_TOKEN=<access policy token with alerts:read and rules:read>
python3 poll_alerts.py
```

The rules have to be in Grafana Cloud first; see
`../observability/grafana-cloud/apply-alert-rules.sh`.

Requires Python 3.11+ (standard library only) and, for the default
agent, Claude Code logged in on this machine (`claude` on `PATH`).

## Configuration

| Variable                | Default                                 |
|-------------------------|-----------------------------------------|
| `ALERTS_URL`            | `http://localhost:9090/api/v1/alerts`   |
| `ALERTS_USER`, `ALERTS_TOKEN` | unset (no auth)                   |
| `POLL_INTERVAL_SECONDS` | `60`                                    |
| `AGENT_COMMAND`         | Claude Code, read-only (below)          |
| `AGENT_TIMEOUT_SECONDS` | `900`                                   |
| `REPO_DIR`              | the repository root                     |
| `INCIDENTS_DIR`         | `./incidents` (git-ignored)             |

`AGENT_COMMAND` receives the prompt on stdin and should print its
report on stdout, so another agent CLI can be swapped in.

## What the agent may do

The default command is

```
claude -p --output-format text --permission-mode dontAsk \
  --allowedTools Read Grep Glob 'Bash(git log:*)' 'Bash(git show:*)' 'Bash(git diff:*)'
```

It can read the repository and its git history, nothing else: no edits,
no network, no push, no deploy. `dontAsk` denies anything not on the
list instead of waiting for an approval nobody is there to give. A
human reads the report and decides what to do (the runbook linked from
the alert says how to roll back).

Alert content (labels, annotations) is passed to the agent inside
marked delimiters and the prompt tells it to treat that as data, not
instructions. Widening the agent's tools (for example letting it open
PRs) would make that boundary matter much more; review the prompt and
permissions before doing so.

## Behaviour

- Only `firing` alerts are handled; `pending` ones are skipped.
- Each firing is handled once: an alert that stays firing isn't re-sent
  every minute. If it resolves and fires again, it's handled again.
- Agents run one at a time in the background, so polling continues
  while one works. Several alerts firing at once queue up.
- A failed poll (API down) is logged and retried next minute. An agent
  that fails or times out leaves its output in `agent.log`.

State is in memory: restarting the poller re-handles alerts that are
still firing.

## Tests

```bash
uv run --with pytest pytest tests
```
