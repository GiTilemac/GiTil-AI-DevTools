# Releasing Snake Arena

How a change gets from a branch to production. For one-time Render and
CI setup, see [deployment.md](deployment.md).

## Environments

| Environment | Branch       | Service            | Deployed by                        | Verified by                        |
|-------------|--------------|--------------------|------------------------------------|------------------------------------|
| Dev         | `main`       | `snake-arena`      | Render auto-deploy on push         | `verify-dev-deploy` (`deploy.yml`) |
| Production  | `production` | `snake-arena-prod` | **Promote to production** workflow | the same workflow (`promote.yml`)  |

Both services use the **same Postgres database** (a Render free-tier
limit). Anything done in dev, such as signups, scores or test data,
also shows up in production.

Render deploys every push to `main` on its own, and CI does not block
it. So merging to `main` **is** a release to dev, even if CI fails.
Only merge PRs that are green. Never push to `production` by hand;
only the Promote workflow moves it.

## Release steps

1. **Open a PR into `main`.** CI runs the backend tests, frontend
   tests (typecheck + Vitest), and the Docker Compose integration suite.
   Merge only when all checks are green.
2. **Verify dev.** In the Actions tab, confirm the **Verify dev deploy**
   job passes. It waits for dev to run the merged commit and then runs
   `integration-tests/` against it. Then try the change on the dev URL:
   sign up or log in, play a game, submit a score, check the
   leaderboard.
3. **Run Promote to production.** In the Actions tab, open **Promote to
   production** and click **Run workflow**. Its first job finds the
   commit dev is running, checks it's on `main` and passed CI, and
   smoke-tests dev. Its summary lists the commits that will ship, and
   warns if `db_models.py` changed.
4. **Approve.** A reviewer for the `production` environment approves
   the waiting job. It fast-forwards `production` to that commit, waits
   for Render to deploy it, and runs `integration-tests/` against
   production.
5. **Check production by hand.** Do a quick manual check of the
   production URL.

Promote ships what dev is **running**, not whatever is newest on
`main`. If a merge is still deploying to dev, wait for it or you'll
promote the commit before it.

## If something goes wrong

- **CI fails on a PR:** fix it on the branch. Nothing has been deployed.
- **Verify dev deploy fails:** don't promote. Fix it on a branch and
  merge the fix.
- **Promote fails before approval:** nothing was deployed. The log says
  which check failed (dev unhealthy, CI not green, or `production`
  can't be fast-forwarded).
- **Promote fails after the push, or users report breakage:** roll back
  first and debug afterwards. Render dashboard → `snake-arena-prod` →
  **Deploys** → last good deploy → **Rollback**. Rolling back turns off
  auto-deploy. Ship the fix through dev, turn auto-deploy back on, then
  promote again (see *Rolling back* in [deployment.md](deployment.md)).

## Database changes

Tables are created on startup by `Base.metadata.create_all()`. It creates
tables that are missing but **does not alter existing ones**. A new or
changed column on an existing table won't be applied on deploy. So:

- Adding a new table is safe.
- Changing an existing table needs a manual migration. Dev and
  production share the database, so a migration run for dev also
  changes it under production, which is still running the older code
  until you promote. Keep migrations backward compatible (add, don't
  rename or drop), and write the steps in the PR. The Promote summary
  flags changes to `db_models.py` as a reminder.

## Checklist

- [ ] PR into `main` is green and merged
- [ ] *Verify dev deploy* passed and manual check on dev done
- [ ] Any schema change is backward compatible with production's code
- [ ] *Promote to production* run and approved
- [ ] Production verification in that run passed
- [ ] Manual check on production done
