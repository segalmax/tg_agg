# Setup Instructions

## 1. Configure Environment

Copy `env.example` to `.env` and update with your MySQL credentials:

```bash
cp env.example .env
```

Edit `.env` with your actual values:
- DB_NAME: your MySQL database name
- DB_USER: your MySQL username
- DB_PASSWORD: your MySQL password
- DB_HOST: usually 'localhost' or '127.0.0.1'
- DB_PORT: usually '3306'
- SECRET_KEY: generate a random secret key
- DEBUG: True for development

## 2. Create MySQL Database

```bash
mysql -u root -p
CREATE DATABASE tg_videos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit;
```

## 3. Load Environment and Run Migrations

```bash
cd /Users/segalmax/tg_agg/tg_site
source ../venv/bin/activate
export $(cat .env | xargs)
python manage.py makemigrations
python manage.py migrate
```

## 4. Create Admin User

```bash
python manage.py createsuperuser
```

## 5. Import JSON Data

```bash
python manage.py import_jsons
```

## 6. Run Development Server

```bash
python manage.py runserver
```

Visit:
- http://localhost:8000 - Main site
- http://localhost:8000/admin - Admin panel

