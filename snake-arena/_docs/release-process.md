# Releasing Snake Arena

How a change gets from a branch to production. For one-time Render and
CI setup, see [deployment.md](deployment.md).

## Environments

| Environment | Branch       | Infrastructure                         | Verified by                                |
|-------------|--------------|----------------------------------------|--------------------------------------------|
| Dev staging | `staging`    | `render.yaml` (dev database)           | `verify-staging-deploy` (`deploy.yml`)     |
| Dev         | `main`       | `render.yaml` (dev database)           | `verify-dev-deploy` (`deploy.yml`)         |
| Production  | `production` | `render.production.yaml` (own database) | `verify-production-deploy` (`deploy.yml`) |

Dev staging and dev share one Postgres database. Production is a
separate copy of the infrastructure with its own database, so nothing
done in dev reaches production data.

Render deploys every push to these branches on its own. CI does not
start or block the deploy. So a push to `staging`, `main` or
`production` **is** a release to that environment, even if CI fails.
Never push to them directly; only merge or fast-forward changes that
are already green.

## Release steps

1. **Open a PR into `staging`.** CI runs the backend tests, frontend
   tests (typecheck + Vitest), and the Docker Compose integration suite.
   Merge only when all checks are green.
2. **Verify dev staging.** In the Actions tab, confirm the **Verify
   staging deploy** job passes, then try the change on the staging URL:
   sign up or log in, play a game, submit a score, check the
   leaderboard.
3. **Promote to dev.** Fast-forward `main` to `staging`:

   ```bash
   git checkout main
   git pull
   git merge --ff-only origin/staging
   git push origin main
   ```

   Confirm the **Verify dev deploy** job passes.
4. **Promote to production.** Fast-forward `production` to `main`, so
   production gets exactly the commit verified in dev:

   ```bash
   git checkout production
   git pull
   git merge --ff-only origin/main
   git push origin production
   ```

5. **Verify production.** Confirm the **Verify production deploy** job
   passes, then do a quick manual check of the production URL.

## If something goes wrong

- **CI fails on a PR:** fix it on the branch. Nothing has been deployed.
- **Verify staging or dev deploy fails:** don't promote. Fix it on a
  branch and send it through `staging` again.
- **Verify production deploy fails, or users report breakage:** roll
  back first and debug afterwards. Render dashboard (production
  workspace) → `snake-arena-prod` → **Deploys** → last good deploy →
  **Rollback**. Rolling back turns off auto-deploy. Turn it back on
  only after the fix has gone through dev.

## Database changes

Tables are created on startup by `Base.metadata.create_all()`. It creates
tables that are missing but **does not alter existing ones**. A new or
changed column on an existing table won't be applied on deploy. So:

- Adding a new table is safe.
- Changing an existing table needs a manual migration. Dev and
  production have separate databases, so run it against each one: dev
  first, then production when the change is promoted. Write the steps
  in the PR.

## Checklist

- [ ] PR into `staging` is green and merged
- [ ] *Verify staging deploy* passed and manual check on staging done
- [ ] `main` fast-forwarded to `staging`; *Verify dev deploy* passed
- [ ] Any schema change reviewed, and migrated on the production
      database if needed (see above)
- [ ] `production` fast-forwarded to `main` and pushed
- [ ] *Verify production deploy* passed
- [ ] Manual check on production done
