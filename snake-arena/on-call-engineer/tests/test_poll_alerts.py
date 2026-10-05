from __future__ import annotations

import dataclasses
import json
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import poll_alerts  # noqa: E402

FIRING = {
    "labels": {"alertname": "GameCreationFailing", "environment": "production", "version": "20261006-120000-abc1234"},
    "annotations": {"summary": "players can't start games", "runbook_url": "https://github.com/x/y/blob/main/r.md"},
    "state": "firing",
    "activeAt": "2026-10-06T10:00:00Z",
    "value": "5e-01",
}


class FakeAlertsAPI:
    def __init__(self) -> None:
        self.alerts: list[dict] = []
        self.auth_headers: list[str | None] = []
        api = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                api.auth_headers.append(self.headers.get("Authorization"))
                body = json.dumps({"status": "success", "data": {"alerts": api.alerts}}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args: object) -> None:
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/api/v1/alerts"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


@pytest.fixture
def api() -> Iterator[FakeAlertsAPI]:
    fake = FakeAlertsAPI()
    yield fake
    fake.server.shutdown()


# A stand-in agent: records its prompt and prints a report.
AGENT = (
    f"{sys.executable} -c \"import sys, pathlib; p = sys.stdin.read(); "
    "pathlib.Path('prompts.log').open('a').write(p + '\\n=====\\n'); print('# Report\\nall good')\""
)


def make(api: FakeAlertsAPI, tmp_path: Path, agent: str = AGENT, **overrides: object) -> poll_alerts.OnCall:
    config = poll_alerts.Config(
        alerts_url=api.url,
        alerts_user=None,
        alerts_token=None,
        poll_interval=60,
        agent_command=poll_alerts.shlex.split(agent),
        agent_timeout=30,
        repo_dir=tmp_path,
        incidents_dir=tmp_path / "incidents",
    )
    return poll_alerts.OnCall(dataclasses.replace(config, **overrides))


def prompts(tmp_path: Path) -> list[str]:
    log = tmp_path / "prompts.log"
    return [p for p in log.read_text().split("\n=====\n") if p.strip()] if log.exists() else []


def test_firing_alert_goes_to_the_agent_once(api: FakeAlertsAPI, tmp_path: Path) -> None:
    api.alerts = [FIRING]
    oncall = make(api, tmp_path)

    assert len(oncall.poll()) == 1
    assert oncall.poll() == []  # still firing: not sent again
    oncall.wait()

    sent = prompts(tmp_path)
    assert len(sent) == 1
    assert '"alertname": "GameCreationFailing"' in sent[0]
    assert "-----BEGIN ALERT-----" in sent[0]
    (incident,) = (tmp_path / "incidents").iterdir()
    assert json.loads((incident / "alert.json").read_text())["labels"]["environment"] == "production"
    assert (incident / "report.md").read_text().startswith("# Report")


def test_pending_alerts_are_ignored(api: FakeAlertsAPI, tmp_path: Path) -> None:
    api.alerts = [{**FIRING, "state": "pending"}]
    oncall = make(api, tmp_path)
    assert oncall.poll() == []
    oncall.wait()
    assert prompts(tmp_path) == []


def test_alert_that_fires_again_is_handled_again(api: FakeAlertsAPI, tmp_path: Path) -> None:
    oncall = make(api, tmp_path)
    api.alerts = [FIRING]
    oncall.poll()
    api.alerts = []  # resolved
    oncall.poll()
    api.alerts = [{**FIRING, "activeAt": "2026-10-06T11:00:00Z"}]  # fires again
    assert len(oncall.poll()) == 1
    oncall.wait()
    assert len(prompts(tmp_path)) == 2


def test_each_distinct_alert_is_handled(api: FakeAlertsAPI, tmp_path: Path) -> None:
    dev = {**FIRING, "labels": {**FIRING["labels"], "environment": "dev"}}
    api.alerts = [FIRING, dev]
    oncall = make(api, tmp_path)
    assert len(oncall.poll()) == 2
    oncall.wait()
    assert len(prompts(tmp_path)) == 2


def test_agent_failure_is_recorded_and_polling_continues(api: FakeAlertsAPI, tmp_path: Path) -> None:
    api.alerts = [FIRING]
    oncall = make(api, tmp_path, agent=f"{sys.executable} -c \"import sys; sys.stderr.write('boom'); sys.exit(3)\"")
    oncall.poll()
    oncall.wait()
    (incident,) = (tmp_path / "incidents").iterdir()
    assert (incident / "agent.log").read_text() == "boom"


def test_missing_agent_binary_does_not_crash(api: FakeAlertsAPI, tmp_path: Path) -> None:
    api.alerts = [FIRING]
    oncall = make(api, tmp_path, agent="definitely-not-a-real-agent-binary")
    oncall.poll()
    oncall.wait()
    (incident,) = (tmp_path / "incidents").iterdir()
    assert "could not start agent" in (incident / "agent.log").read_text()


def test_basic_auth_is_sent_when_configured(api: FakeAlertsAPI, tmp_path: Path) -> None:
    oncall = make(api, tmp_path, alerts_user="123", alerts_token="secret")
    oncall.poll()
    assert api.auth_headers[-1] == "Basic MTIzOnNlY3JldA=="


def test_default_agent_is_read_only() -> None:
    command = poll_alerts.shlex.split(poll_alerts.DEFAULT_AGENT_COMMAND)
    assert command[:2] == ["claude", "-p"]
    assert "dontAsk" in command
    allowed = command[command.index("--allowedTools") + 1 :]
    assert not any(tool.startswith(("Edit", "Write", "Bash(git push", "Bash(curl")) for tool in allowed)
