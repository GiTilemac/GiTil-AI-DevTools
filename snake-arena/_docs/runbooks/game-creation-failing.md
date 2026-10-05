# Runbook: GameCreationFailing

**Alert:** at least 20% of game starts (and at least 3) failed over 10
minutes, sustained for 5 minutes, in one environment and version.
`invalid_mode` rejections don't count: the frontend only sends valid
modes, so they come from other clients.
Defined in `observability/prometheus/rules/snake-arena-alerts.yml`.

**Impact:** players press a key to start and the backend rejects or
fails `POST /games`. Gameplay itself runs in the browser and isn't
blocked (the frontend ignores the failure), so the visible effect is
missing games in the metrics. If the failures come from the backend
being unhealthy, everything else (leaderboard, login) is likely failing
too.

The alert's labels tell you where: `environment`, `version`, `service`.
Its `dashboard_url` opens the games dashboard filtered to them.

## 1. What kind of failure?

On the dashboard, look at **Creation failures** by `error_type`:

| `error_type`       | Meaning                                        | Likely cause |
|--------------------|------------------------------------------------|--------------|
| `invalid_mode`     | Request had a missing or unknown `mode`. Not part of the alert, but visible on the dashboard | A client/bot sending junk; or, if it jumps after a release, frontend and backend disagreeing on modes |
| `too_many_games`   | 10,000 sessions in memory already              | Abandoned sessions not expiring, or a flood of starts (abuse) |
| an exception class (e.g. `RuntimeError`) | Unexpected error in the backend | A bug, or a dependency failing |

## 2. Did it start with a deploy?

Compare the alert's `version` with the previous one:

- **Active games by environment and version** on the dashboard shows
  when the version changed.
- `curl https://<service>/health` shows the version running now.

If the failures began with the new version, **roll back first, debug
after**:

- **Production:** Render dashboard → `snake-arena-prod` → Events →
  previous deploy → **Rollback**, or call the deploy hook with the
  previous image tag (see *Rolling back* in `../deployment.md`).
- **Dev:** revert the change on `main`; CI deploys the revert.

## 3. Find the error

- **Logs:** Explore → Loki →
  `{service_name="snake-arena", deployment_environment_name="<environment>"} |= "games"`.
  Unexpected exceptions are logged by uvicorn with a traceback.
- **Traces:** Explore → Tempo →
  `{resource.deployment.environment="<environment>" && span.http.route="/games" && status=error}`.
  Each trace links to its logs.

## 4. Fix and verify

Ship the fix through dev, then promote (`release-process.md`). The
alert resolves on its own once the failure rate has been under 20% (or
under 3 failures) for 10 minutes.

## Tuning

If this fires without real impact, adjust the thresholds in the rule
and its promtool tests (`snake-arena-alerts.test.yml`) together.
