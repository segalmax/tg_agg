web: cd tg_site && python manage.py migrate && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
worker: python scripts/fetch/fetch_all_tg_chanels_to_db.py

