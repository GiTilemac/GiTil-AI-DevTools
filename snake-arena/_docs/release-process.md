# Releasing Snake Arena

How a change gets from a branch to production. For one-time Render and
CI setup, see [deployment.md](deployment.md).

## Environments

| Environment | Branch    | Deployed by                     | Verified by                         |
|-------------|-----------|---------------------------------|-------------------------------------|
| Staging     | `staging` | Render auto-deploy on push      | `verify-staging-deploy` (`deploy.yml`) |
| Production  | `main`    | Render auto-deploy on push      | `verify-production-deploy` (`deploy.yml`) |

Both services use the **same Postgres database** (a Render free-tier
limit). Anything you do on staging, such as signups, scores or test
data, also shows up on the production leaderboard.

Render deploys every push to these branches on its own. CI does not
start or block the deploy. So a push to `staging` or `main` **is** a
release, even if CI fails. Never push to them directly; only merge
changes that are already green.

## Release steps

1. **Open a PR into `staging`.** CI runs the backend tests, frontend
   tests (typecheck + Vitest), and the Docker Compose integration suite.
   Merge only when all checks are green.
2. **Wait for the staging deploy.** Render deploys automatically. In the
   Actions tab, confirm the **Verify staging deploy** job passes. It
   waits for `/health` and then runs `integration-tests/` against the
   live staging URL.
3. **Check staging by hand.** Open the staging URL and try the change:
   sign up or log in, play a game, submit a score, check the
   leaderboard.
4. **Promote to production.** Fast-forward `main` to `staging` so that
   production gets exactly the commit you verified:

   ```bash
   git checkout main
   git pull
   git merge --ff-only origin/staging
   git push origin main
   ```

5. **Verify production.** Confirm the **Verify production deploy** job
   passes, then do a quick manual check of the production URL.

## If something goes wrong

- **CI fails on a PR:** fix it on the branch. Nothing has been deployed.
- **Verify staging deploy fails:** don't promote. Fix it on a branch
  and send it through staging again.
- **Verify production deploy fails, or users report breakage:** roll
  back first and debug afterwards. Follow the README's *Rolling back a
  bad deploy* section: Render dashboard → service → **Deploys** →
  last good deploy → **Rollback**. Rolling back turns off auto-deploy.
  Turn it back on only after the fix has gone through staging.

## Database changes

Tables are created on startup by `Base.metadata.create_all()`. It creates
tables that are missing but **does not alter existing ones**. A new or
changed column on an existing table won't be applied on deploy, and
staging and production share one database. So:

- Adding a new table is safe.
- Changing an existing table needs a manual migration, planned with
  both environments in mind, because they share the data. Write the
  steps in the PR.

## Checklist

- [ ] PR into `staging` is green and merged
- [ ] *Verify staging deploy* passed
- [ ] Manual check on staging done
- [ ] Any schema change reviewed (see above)
- [ ] `main` fast-forwarded to `staging` and pushed
- [ ] *Verify production deploy* passed
- [ ] Manual check on production done
