# Releasing Snake Arena

How a change gets from a branch to production. For the pipeline and
one-time Render, registry and CI setup, see
[deployment.md](deployment.md).

## Environments

| Environment | Service            | Gets                                  | Deployed by                        |
|-------------|--------------------|---------------------------------------|------------------------------------|
| Dev         | `snake-arena`      | every image CI builds from `main`     | CI (`build` → `deploy-dev`)        |
| Production  | `snake-arena-prod` | the image dev is running, when asked  | **Promote to production** workflow |

Every image is built once, tagged `YYYYMMDD-HHMMSS-shortsha`, and
pushed to `ghcr.io/gitilemac/snake-arena`. Production runs the exact
image that ran in dev; nothing is rebuilt. `/health` on either service
reports which tag it's running.

Both services use the **same Postgres database** (a Render free-tier
limit). Anything done in dev, such as signups, scores or test data,
also shows up in production.

## Release steps

1. **Open a PR into `main`.** CI runs the backend tests, frontend
   tests (typecheck + Vitest), and the Docker Compose integration suite.
   Merge only when all checks are green.
2. **Let CI ship it to dev.** On the merge, CI runs the tests again,
   then **Build and push image** and **Deploy to dev**. The deploy job
   waits for dev to run the new tag and runs `integration-tests/`
   against it. Then try the change on the dev URL: sign up or log in,
   play a game, submit a score, check the leaderboard.
3. **Run Promote to production.** In the Actions tab, open **Promote to
   production** and click **Run workflow**. Its first job reads the tag
   dev is running and checks the image is in the registry. Its summary
   lists the commits that will ship, and warns if `db_models.py`
   changed.
4. **Approve** (only if the `production` environment has required
   reviewers). The deploy then has Render pull that image, waits for
   production to report the tag, and runs `integration-tests/` against
   production.
5. **Check production by hand.** Do a quick manual check of the
   production URL.

Promote ships what dev is **running**, not whatever is newest on
`main`. If a merge is still on its way to dev, wait for **Deploy to
dev** to finish or you'll promote the image before it.

## If something goes wrong

- **CI fails on a PR:** fix it on the branch. Nothing was built.
- **Tests fail on `main`:** no image is built and dev isn't touched.
- **Deploy to dev fails:** dev may be running the new image (if only
  the smoke tests failed) or still the old one (if it never became
  live). Don't promote. Fix it on a branch and merge the fix.
- **Promote fails before the deploy starts:** nothing was deployed. The
  log says which check failed.
- **Production deploy fails, or users report breakage:** roll back
  first and debug afterwards (see *Rolling back* in
  [deployment.md](deployment.md)), then ship the fix through dev and
  promote again.

## Database changes

Tables are created on startup by `Base.metadata.create_all()`. It creates
tables that are missing but **does not alter existing ones**. A new or
changed column on an existing table won't be applied on deploy. So:

- Adding a new table is safe.
- Changing an existing table needs a manual migration. Dev and
  production share the database, so a migration run for dev also
  changes it under production, which is still running the older image
  until you promote. Keep migrations backward compatible (add, don't
  rename or drop), and write the steps in the PR. The Promote summary
  flags changes to `db_models.py` as a reminder.

## Checklist

- [ ] PR into `main` is green and merged
- [ ] *Deploy to dev* passed and manual check on dev done
- [ ] Any schema change is backward compatible with production's image
- [ ] *Promote to production* run (and approved, if reviewers are set)
- [ ] Production deploy and smoke tests in that run passed
- [ ] Manual check on production done
