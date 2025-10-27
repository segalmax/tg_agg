# Telegram Aggregator

A Django-based web application for aggregating and displaying Telegram channel posts with advanced filtering, searching, and video playback capabilities.

## Features

- 📺 Video playback with thumbnails directly from Telegram posts
- 🔍 Advanced search and filtering (by channel, media type, views, date range)
- ⬆️ Sorting options (date, views, forwards, replies)
- 📊 Pagination with filter persistence
- 🎬 Support for videos and photos

## Setup

1. **Clone the repository**
```bash
git clone https://github.com/segalmax/tg_agg.git
cd tg_agg
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
Create a `.env` file in `tg_site/` directory:
```
SECRET_KEY=your-secret-key-here
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306
```

5. **Run migrations**
```bash
cd tg_site
python manage.py migrate
```

6. **Create superuser**
```bash
python manage.py createsuperuser
```

7. **Run the server**
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` to view the application.

## Data Import

Use `fetch_telegram_history.py` to fetch posts from Telegram channels, then import them using:
```bash
python manage.py import_jsons
```

## Tech Stack

- Django 4.2.25
- MySQL
- Telethon (Telegram API)
- HTML/CSS/JavaScript

