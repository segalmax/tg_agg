web: cd tg_site && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
worker: python scripts/fetch/fetch_all_tg_chanels_to_db.py

