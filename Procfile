web: cd tg_site && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
worker: python monitor_all_channels.py

