# 🚂 Railway Deployment Guide

## Step 1: Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign in with GitHub

## Step 2: Create New Project
1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose your **`tg_agg`** repository
4. Click **"Deploy Now"**

## Step 3: Add MySQL Database
1. In your project, click **"+ New"**
2. Select **"Database"** → **"Add MySQL"**
3. Railway will create a MySQL instance and auto-generate credentials

## Step 4: Set Environment Variables
Click on your web service → **"Variables"** tab → Add these:

### Required Variables:
```
SECRET_KEY=your-secret-key-here-make-it-long-and-random
DEBUG=False
ALLOWED_HOSTS=your-app.up.railway.app
DB_NAME=${{MySQL.MYSQLDB_DATABASE}}
DB_USER=${{MySQL.MYSQLDB_USER}}
DB_PASSWORD=${{MySQL.MYSQLDB_PASSWORD}}
DB_HOST=${{MySQL.MYSQLDB_HOST}}
DB_PORT=${{MySQL.MYSQLDB_PORT}}
```

### Notes:
- For `SECRET_KEY`: Generate a random string (50+ characters)
  - Run: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
- The `${{MySQL.XXX}}` variables auto-reference your MySQL service
- Replace `your-app.up.railway.app` with your actual Railway domain (shown after deployment)

## Step 5: Deploy!
1. Railway will automatically deploy after you save variables
2. Click **"Settings"** → **"Networking"** → **"Generate Domain"**
3. Your site will be live at: `https://your-app.up.railway.app`

## Step 6: Run Database Migrations
In your project:
1. Click on your web service
2. Go to **"Settings"** → **"Deploy"**
3. Or Railway will auto-run migrations (configured in `railway.toml`)

## Step 7: Create Admin User
1. Go to your service → **"Settings"** → **"Variables"**
2. Create a one-time deployment command:
   - Click service → Top right menu → **"Run a Command"**
   - Run: `cd tg_site && python manage.py createsuperuser`
   - Follow prompts to create admin user

## Step 8: Import Your Data (Optional)
If you have existing data:
1. Export your local database
2. Use Railway's MySQL connection string to import
3. Or re-run your `import_jsons` command on Railway

## Updating Your Site
Just push to GitHub:
```bash
git add .
git commit -m "Update"
git push origin main
```
Railway auto-deploys on every push! 🚀

## Monitoring
- **Logs**: Click your service → "Deployments" → View logs
- **Metrics**: See CPU, memory, bandwidth usage in dashboard
- **Costs**: Monitor usage in "Account" → "Usage"

## Troubleshooting
- **Build fails**: Check logs for missing dependencies
- **Database connection fails**: Verify environment variables
- **Static files not loading**: Make sure `whitenoise` is installed
- **500 errors**: Set `DEBUG=True` temporarily to see errors (then turn back off!)

## Cost Estimate
- **Free tier**: $5 credit/month
- **Typical usage**: $5-10/month for small traffic
- **Components**: Web service + MySQL database

---

**Need help?** Railway has great docs: [docs.railway.app](https://docs.railway.app)

