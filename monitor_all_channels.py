#!/usr/bin/env python3
"""
monitor_all_channels.py
----------------------
Continuously monitor all channels in the database for new posts.
Runs every 60 seconds, checking all channels for updates.

Designed to run on Railway as a background service.
"""
import os
import sys
import time
from datetime import datetime, timezone

# Django setup
PROJECT_DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(PROJECT_DIR, "tg_site"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from videos.models import Channel, Post
from telethon.sync import TelegramClient
from telethon.tl.types import Message

# Configuration
DEFAULT_SINCE_DATE = datetime(2023, 10, 1, tzinfo=timezone.utc)
CHECK_INTERVAL = 60  # seconds
BATCH_SIZE = 100  # messages per request
RATE_LIMIT_DELAY = 2  # seconds between channels


def save_message(msg: Message, channel: Channel) -> bool:
    """Upsert message into database. Returns True if new post."""
    media_type = None
    video_data = None
    has_media = bool(msg.media)

    if msg.media:
        media_type = type(msg.media).__name__
        if hasattr(msg.media, "document") and msg.media.document:
            doc = msg.media.document
            video_data = {
                "duration": getattr(doc, "duration", None),
                "size": getattr(doc, "size", None),
            }

    defaults = {
        "date": msg.date.astimezone(timezone.utc),
        "text": msg.text or "",
        "views": getattr(msg, "views", 0) or 0,
        "forwards": getattr(msg, "forwards", 0) or 0,
        "replies": getattr(msg.replies, "replies", 0) if msg.replies else 0,
        "link": f"https://t.me/{channel.username}/{msg.id}",
        "has_media": has_media,
        "media_type": media_type,
        "video_data": video_data,
    }

    post, created = Post.objects.update_or_create(
        channel=channel, telegram_id=msg.id, defaults=defaults
    )
    return created


def check_channel(client: TelegramClient, channel: Channel, since_date: datetime) -> int:
    """Check a single channel for new posts. Returns count of new posts."""
    try:
        entity = client.get_entity(channel.username)
        new_count = 0
        
        # Fetch recent messages
        messages = client.get_messages(entity, limit=BATCH_SIZE)
        
        for msg in messages:
            # Skip if older than since_date
            if msg.date.replace(tzinfo=timezone.utc) < since_date:
                break
                
            # Save message
            created = save_message(msg, channel)
            if created:
                new_count += 1
                print(f"  ✅ {channel.username} | {msg.id} | {msg.date.date()}")
            else:
                # Stop on first existing post (gap-fill mode)
                break
        
        return new_count
        
    except Exception as e:
        print(f"  ❌ Error checking {channel.username}: {e}")
        return 0


def monitor_loop():
    """Main monitoring loop."""
    # Get API credentials
    api_id = int(os.getenv("API_ID", "0"))
    api_hash = os.getenv("API_HASH", "")
    
    if api_id == 0 or not api_hash:
        print("❌ API_ID / API_HASH not set in environment variables")
        sys.exit(1)
    
    print("🚀 Starting channel monitor service...")
    print(f"⏱️  Check interval: {CHECK_INTERVAL}s")
    print(f"📅 Default since date: {DEFAULT_SINCE_DATE.date()}")
    print("=" * 70)
    
    # Initialize Telegram client
    client = TelegramClient("session", api_id, api_hash)
    
    with client:
        iteration = 0
        while True:
            iteration += 1
            start_time = time.time()
            
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Check #{iteration}")
            print("-" * 70)
            
            # Get all channels from database
            channels = Channel.objects.all().order_by('username')
            
            if not channels:
                print("⚠️  No channels in database")
            
            total_new = 0
            for channel in channels:
                print(f"📺 Checking {channel.username}...")
                new_posts = check_channel(client, channel, DEFAULT_SINCE_DATE)
                total_new += new_posts
                
                if new_posts > 0:
                    print(f"  🎉 {new_posts} new post(s) added")
                else:
                    print(f"  ✓ No new posts")
                
                # Rate limiting between channels
                time.sleep(RATE_LIMIT_DELAY)
            
            elapsed = time.time() - start_time
            print("-" * 70)
            print(f"✅ Check complete | New posts: {total_new} | Time: {elapsed:.1f}s")
            
            # Wait for next check
            sleep_time = max(0, CHECK_INTERVAL - elapsed)
            if sleep_time > 0:
                print(f"😴 Sleeping for {sleep_time:.0f}s until next check...")
                time.sleep(sleep_time)


if __name__ == "__main__":
    try:
        monitor_loop()
    except KeyboardInterrupt:
        print("\n\n👋 Monitor service stopped")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

