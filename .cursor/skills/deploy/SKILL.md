---
name: deploy
description: Full deploy workflow for tg_agg (Railway + GitHub). Use when the user runs /deploy, asks to deploy, ship, release, or push to production. Covers pre-flight checks, feature branch, PR creation, polling for merge, Railway redeploy, smoke test, and rollback.
---

# Deploy

Full workflow: feature branch → CI → PR → merge → Railway auto-deploy → smoke test.

## Commit message convention

Always use conventional commits:
- `feat:` new feature
- `fix:` bug fix
- `chore:` tooling / deps / config
- `docs:` documentation only

## Step 1 — Pre-flight checks

Run all of these. Stop and fix anything that fails.

```bash
# 1. Nothing uncommitted
git status

# 2. Nothing unpushed
git log origin/HEAD..HEAD

# 3. Tests
cd tg_site && python manage.py test videos.tests --noinput

# 4. Lint
ruff check tg_site/

# 5. Unapplied migrations (warn, not hard-block)
python manage.py showmigrations | grep '\[ \]'
```

## Step 2 — Feature branch + push

```bash
git checkout -b feat/<short-description>
git add .
git commit -m "feat: <description>"
git push -u origin feat/<short-description>
```

## Step 3 — Open PR

```bash
gh pr create \
  --title "feat: <description>" \
  --body "$(cat .github/pull_request_template.md)" \
  --base main
```

Tell the user: **"PR is open — review it in GitHub and merge when ready. I'll wait."**

## Step 4 — Poll for merge

Poll every 15 seconds until `state == "MERGED"`:

```bash
gh pr view <number> --json state --jq '.state'
```

GitHub Actions CI (`ci` job) must pass before the merge button is enabled (branch protection enforces this).

Once MERGED:
```bash
git checkout main && git pull
```

## Step 5 — Wait for Railway auto-deploy

Railway auto-deploys both services on merge to main. Do NOT run `railway redeploy`.

Poll every 15 seconds (up to ~5 minutes). Each iteration, run ALL of these:

```bash
railway deployment list --service web
railway deployment list --service telegram-monitor
railway logs --lines 10 --service web
railway logs --lines 10 --service telegram-monitor
```

**CRASHED detection is tricky:** Railway's restart policy immediately creates new BUILDING deployments on top of a CRASHED one, pushing CRASHED down the list. Always scan ALL entries in `deployment list` output, not just line 1. If CRASHED appears anywhere in the recent entries, stop and report it to the user.

Stop when both services show SUCCESS as the most recent entry AND logs show no errors.

Note: never pipe `railway logs` to `tail` — it streams and never sends EOF so tail hangs forever. Use `--lines N` instead.

If `telegram-monitor` crashes with `AuthKeyDuplicatedError`, regenerate the session:
```bash
python scripts/generate_session_string.py
railway variables --service telegram-monitor --set "SESSION_STRING=<paste>"
```
Then poll again until both show SUCCESS.

## Step 6 — Smoke test

Use a browser tool to:
1. Open `https://web-production-61089.up.railway.app`
2. Verify the page loads (no 500 / crash page)
3. Verify at least one video card is visible in the grid

If PR touched any template / CSS / JS:
4. Click a video card → verify the modal opens
5. Take a screenshot and show it to the user

Report results to the user.

## Step 7 — Rollback (if any check fails)

```bash
railway rollback --service web
railway rollback --service telegram-monitor
```

Then re-run smoke test to confirm rollback succeeded.

## Reference

- Railway services & env vars: `docs/RAILWAY_DEPLOY.md`
- Migration incidents: `docs/RAILWAY_DEPLOY.md` → InconsistentMigrationHistory section
- CI workflow: `.github/workflows/ci.yml`
- PR template: `.github/pull_request_template.md`
