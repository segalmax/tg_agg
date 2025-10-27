# Railway Monitor Service Setup

## Overview
This sets up a background worker service on Railway that monitors all channels in the database every 60 seconds for new posts.

## Step 1: Add Environment Variables to Railway

Go to your Railway project → **Web Service** → **Variables** and add:

```
API_ID=25486530
API_HASH=178cf13588f57714d72abed67409221a
```

## Step 2: Upload Telegram Session File

The monitor needs your authenticated Telegram session (`session.session` file).

### Option A: Add to Git (Temporarily)
```bash
# 1. Remove session.session from .gitignore temporarily
sed -i.bak '/session.session/d' .gitignore

# 2. Commit and push
git add session.session
git commit -m "Add Telegram session for monitor"
git push

# 3. Restore .gitignore
mv .gitignore.bak .gitignore
git add .gitignore
git commit -m "Restore .gitignore"
git push
```

### Option B: Manual Upload via Railway CLI
```bash
railway login
railway link
railway up session.session
```

## Step 3: Deploy Worker Service

### Option A: Same Service (Simplest)
Railway will automatically detect the `Procfile` and run the `worker` process alongside the web service.

1. Push the code:
   ```bash
   git add .
   git commit -m "Add channel monitor service"
   git push
   ```

2. In Railway dashboard → Your service → **Settings** → **Deploy**
   - Verify the deploy succeeded

3. Check logs:
   ```bash
   railway logs
   ```
   
   You should see output like:
   ```
   🚀 Starting channel monitor service...
   ⏱️  Check interval: 60s
   📅 Default since date: 2023-10-01
   ```

### Option B: Separate Worker Service (Recommended for scaling)

1. In Railway dashboard, click **+ New** → **Empty Service**
2. Name it: `telegram-monitor`
3. Connect the same GitHub repo
4. Add the same environment variables (DB credentials, API_ID, API_HASH)
5. In **Settings** → **Start Command**, set:
   ```
   python monitor_all_channels.py
   ```

## Step 4: Verify It's Running

Check Railway logs:
```bash
railway logs --service telegram-monitor
```

Or in the Railway dashboard, you should see:
```
[2025-10-27 12:00:00] 🔄 Check #1
----------------------------------------------------------------------
📺 Checking abualiexpress...
  ✓ No new posts
📺 Checking Warlife3...
  ✓ No new posts
----------------------------------------------------------------------
✅ Check complete | New posts: 0 | Time: 4.2s
😴 Sleeping for 56s until next check...
```

## Configuration

Edit `/Users/segalmax/tg_agg/monitor_all_channels.py` to adjust:

- `CHECK_INTERVAL = 60` - Seconds between checks (default: 60)
- `DEFAULT_SINCE_DATE` - How far back to check (default: Oct 1, 2023)
- `BATCH_SIZE = 100` - Messages to fetch per channel (default: 100)
- `RATE_LIMIT_DELAY = 2` - Seconds between channels (default: 2)

## Troubleshooting

### "No session.session file"
Make sure you uploaded the session file (Step 2).

### "API_ID / API_HASH not set"
Add environment variables in Railway dashboard (Step 1).

### Monitor not running
- Check Railway logs for errors
- Verify the service is running (not paused)
- Check that `worker` process type is enabled

### Too many API requests
Increase `RATE_LIMIT_DELAY` or `CHECK_INTERVAL` in the script.

---

## Quick Deploy (All Steps)

```bash
# 1. Set environment variables in Railway dashboard (API_ID, API_HASH)

# 2. Commit and push
git add monitor_all_channels.py Procfile RAILWAY_MONITOR_SETUP.md
git commit -m "Add channel monitor service"

# 3. Temporarily add session file
sed -i.bak '/session.session/d' .gitignore
git add session.session
git commit -m "Add Telegram session"
git push

# 4. Restore .gitignore
mv .gitignore.bak .gitignore
git add .gitignore
git commit -m "Restore .gitignore"
git push

# 5. Check logs
railway logs
```

Done! Your monitor will now run every 60 seconds, checking all channels for new posts.

