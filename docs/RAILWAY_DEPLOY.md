# Railway Deployment Operations

## Services
- `web`: Django + Gunicorn. Railway start command runs `cd tg_site && python manage.py migrate && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`.
- `MySQL`: Managed database provisioned by Railway, volume mounted at `/var/lib/mysql`.
- `telegram-monitor`: Background fetcher; start command is configured in the Railway UI as `python scripts/fetch/fetch_all_tg_chanels_to_db.py`.

## Common CLI Tasks
- Show current project/services: `railway status --json`.
- Tail worker logs: `railway logs --service telegram-monitor --lines 100`.
- Tail web logs: `railway logs --service web --lines 100`.
- Tail MySQL logs (rarely needed): `railway logs --service mysql --lines 50`.
- Redeploy after config changes: `railway redeploy --service web` or `--service telegram-monitor`.

## Environment Variables
- Manage shared env vars in the Railway dashboard under each service → **Variables**.
- Web and monitor services rely on `API_ID`, `API_HASH`, `SESSION_STRING`, and Django DB credentials.
- MySQL credentials are auto-injected (`MYSQL_*`). Use them in local `.env` for parity.

## Operational Notes
- The worker should stream logs once per minute when healthy; absence of new entries means the service crashed.
- When changing the fetch script path, update the Railway UI start command (Deploy section) and redeploy.
- `railway run --service telegram-monitor -- python -m json.tool` is handy for testing env vars without redeploying.

## Local Development Setup
To run locally with production data, get Railway credentials:
1. **Get DB credentials**: `railway variables --service web | grep DB_`
2. **Get secrets**: `railway variables --service web | grep -E "SECRET_KEY|API_"` 
3. **Create `.env` file** in `tg_site/` directory with these keys:
   - `SECRET_KEY`, `DEBUG=True`
   - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` (use `mainline.proxy.rlwy.net`), `DB_PORT`
   - `API_ID`, `API_HASH`, `SESSION_STRING` (for Telegram fetcher only)
4. **Start server**: `cd tg_site && source ../venv/bin/activate && python manage.py runserver`
5. **Test connection**: `curl -I http://localhost:8000/` should return `200 OK`
6. **Debug UI**: Use Chrome DevTools MCP to investigate JS issues, check console for errors
7. **Common issues**: Missing env vars cause `KeyError`, wrong DB host causes connection refused
8. **Note**: Production uses Railway's internal `mysql.railway.internal`, local dev uses `mainline.proxy.rlwy.net:43278`

## Incident Checklist
1. Check worker logs for stack traces.
2. Confirm `when_updated` advancing via Django shell (`python manage.py shell`).
3. If stuck, redeploy worker and verify the start command still references the fetch script.