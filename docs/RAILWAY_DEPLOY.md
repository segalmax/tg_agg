# Railway Deployment

## Services
- `web`: Django + Gunicorn on pgvector DB
- `telegram-monitor`: Background Telegram fetcher, writes to pgvector DB
- `pgvector`: PostgreSQL + pgvector extension (production DB)
- `MySQL`: Legacy, no longer used

## Start Commands (Railway UI → Deploy section)
- `web`: `cd tg_site && python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
- `telegram-monitor`: `python scripts/fetch/fetch_all_tg_chanels_to_db.py`

## Environment Variables
Both `web` and `telegram-monitor` need:

| Var | Value |
|-----|-------|
| `DB_HOST` | `pgvector.railway.internal` (internal) |
| `DB_PORT` | `5432` |
| `DB_NAME` | `railway` |
| `DB_USER` | `postgres` |
| `DB_PASSWORD` | from Railway pgvector service |
| `SECRET_KEY` | Django secret key |
| `API_ID`, `API_HASH` | Telegram app credentials |
| `SESSION_STRING` | Telegram session (monitor only) |
| `ALLOWED_HOSTS` | `web-production-61089.up.railway.app` |
| `DEBUG` | `False` |
| `DAYS_BACK` | Optional. Defaults to `7`. Set to `70` temporarily for backfill. |

## CLI Cheatsheet
```bash
# Check status
railway status

# View env vars for a service
railway variables --service web --kv
railway variables --service telegram-monitor --kv

# Set / unset an env var
railway variables --service telegram-monitor --set "DAYS_BACK=70"
railway variables --service telegram-monitor --unset "DAYS_BACK"

# Redeploy
railway redeploy --service web
railway redeploy --service telegram-monitor

# Logs (stream)
railway logs --service web
railway logs --service telegram-monitor
```

## Local Development
```bash
# 1. Get prod DB credentials
railway variables --service web --kv | grep DB_

# 2. Create tg_site/.env with:
#    SECRET_KEY, DEBUG=True
#    DB_HOST=shinkansen.proxy.rlwy.net, DB_PORT=36019, DB_NAME=railway, DB_USER=postgres, DB_PASSWORD=...
#    API_ID, API_HASH (optional, for fetcher only)

# 3. Run
cd tg_site && source ../.venv/bin/activate && python manage.py runserver
```

## Backfill Procedure
To backfill historical data (e.g. after switching DB):
1. `railway variables --service telegram-monitor --set "DAYS_BACK=70"`
2. Wait ~15 min for fetcher to complete one cycle
3. `railway variables --service telegram-monitor --unset "DAYS_BACK"`

## Incident Checklist
1. Check Railway dashboard — service status and recent deploy logs
2. Get crash logs via Railway API or `railway logs --service web`
3. Common causes: missing env var, DB connection failure, bad migration
4. After env var changes, redeploy the affected service

### `InconsistentMigrationHistory` (videos.0001 before 0000_enable_pgvector_extension)
Happens if production already had `videos.0001_initial` applied, then `0000_enable_pgvector_extension` was added as its dependency. The extension already exists on the pgvector service; Django only needs the history row.

From repo root, using the **public** DB URL (resolves from your laptop):

```bash
railway run --service pgvector -- bash -lc 'psql "$DATABASE_PUBLIC_URL" -v ON_ERROR_STOP=1 -c "INSERT INTO django_migrations (app, name, applied) SELECT '\''videos'\'', '\''0000_enable_pgvector_extension'\'', NOW() WHERE NOT EXISTS (SELECT 1 FROM django_migrations WHERE app = '\''videos'\'' AND name = '\''0000_enable_pgvector_extension'\'');"'
```

Then `railway redeploy --service web`.
