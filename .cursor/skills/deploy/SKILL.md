---
name: deploy
description: Full deploy workflow for tg_agg (Railway + GitHub). Use when the user runs /deploy, asks to deploy, ship, release, or push to production. Covers pre-flight checks, feature branch, PR creation, polling for merge, Railway redeploy, smoke test, and rollback.
---

# Deploy

Full workflow: feature branch → CI → PR → merge → Railway redeploy → smoke test.

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

## Step 5 — Railway redeploy

```bash
railway redeploy --service web
railway redeploy --service telegram-monitor
```

Poll `railway logs --service web` every 15 seconds until you see `Booting worker` (success) or an exception traceback (failure). Max wait: 3 minutes.

## Step 6 — Browser smoke test

Use the `cursor-ide-browser` MCP to:
1. Open `https://web-production-61089.up.railway.app`
2. Verify the page loads (no 500 / crash page)
3. Verify at least one video card is visible in the grid

## Step 7 — Rollback (if smoke test fails)

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
