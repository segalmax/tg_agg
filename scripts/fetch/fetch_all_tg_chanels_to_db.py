#!/usr/bin/env python3
"""
fetch_all_tg_chanels_to_db.py
------------------------------
Continuously fetch all posts from last 7 days for all channels in database.
Runs every 60 seconds, fetching and updating posts from the sliding 7-day window.

Designed to run on Railway as a background service.
"""
import os
import sys
import time
from datetime import datetime, timedelta, timezone

# Django setup
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "tg_site"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from videos.models import Channel, Post
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Message

# Configuration
DAYS_BACK = 7  # Always fetch last 7 days
CHECK_INTERVAL = 60  # seconds
RATE_LIMIT_DELAY = 2  # seconds between channels


def save_message(msg: Message, channel: Channel) -> tuple[bool, bool]:
    """
    Upsert message into database.
    Returns (created, updated) - True if new post, True if existing post was updated.
    """
    # Skip posts with views=1 (duplicate/edit posts)
    msg_views = getattr(msg, "views", 0) or 0
    if msg_views == 1:
        return False, False
    
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

    now = datetime.now(timezone.utc)
    defaults = {
        "date": msg.date.astimezone(timezone.utc),
        "text": msg.text or "",
        "views": msg_views,
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
    
    if created:
        return True, False

    post.when_updated = now
    post.save(update_fields=["when_updated"])
    return False, True


def check_channel(client: TelegramClient, channel: Channel, since_date: datetime) -> tuple[int, int]:
    """
    Check a single channel for posts in the last 7 days.
    Returns (new_count, updated_count).
    Fetches all messages from since_date to now in batches.
    """
    try:
        entity = client.get_entity(channel.username)
        new_count = 0
        updated_count = 0
        
        # Fetch messages in batches, starting from newest
        # Stop when we encounter messages older than since_date
        messages = []
        offset_id = 0  # Start from newest
        
        while True:
            batch = client.get_messages(entity, limit=100, offset_id=offset_id)
            if not batch:
                break
            
            # Filter messages within date range
            batch_in_range = []
            for msg in batch:
                msg_date = msg.date.replace(tzinfo=timezone.utc) if msg.date.tzinfo is None else msg.date
                if msg_date >= since_date:
                    batch_in_range.append(msg)
                else:
                    # Messages older than since_date - we're done
                    break
            
            messages.extend(batch_in_range)
            
            # If batch is empty or we hit old messages, we're done
            if not batch_in_range or len(batch_in_range) < len(batch):
                break
            
            # Set offset to oldest message ID for next batch
            offset_id = batch[-1].id
        
        # Process all messages (both new and existing)
        for msg in messages:
            # Skip if older than since_date (safety check)
            msg_date = msg.date.replace(tzinfo=timezone.utc) if msg.date.tzinfo is None else msg.date
            if msg_date < since_date:
                continue
            
            created, updated = save_message(msg, channel)
            if created:
                new_count += 1
                print(f"  ✅ NEW {channel.username} | {msg.id} | {msg.date.date()}")
            elif updated:
                updated_count += 1
                print(f"  🔄 UPD {channel.username} | {msg.id} | {msg.date.date()}")
        
        return new_count, updated_count
        
    except Exception as e:
        print(f"  ❌ Error checking {channel.username}: {e}")
        return 0, 0


def fetch_loop():
    """Main fetching loop."""
    # Get API credentials
    api_id = int(os.getenv("API_ID", "0"))
    api_hash = os.getenv("API_HASH", "")
    
    if api_id == 0 or not api_hash:
        print("❌ API_ID / API_HASH not set in environment variables")
        sys.exit(1)
    
    print("🚀 Starting channel fetch service...")
    print(f"⏱️  Check interval: {CHECK_INTERVAL}s")
    print(f"📅 Fetching last {DAYS_BACK} days (sliding window)")
    print("=" * 70)
    
    # Initialize Telegram client
    # Use session string (Railway) or session file (local)
    session_string = os.getenv("SESSION_STRING")
    if session_string:
        print("🔑 Using session string from environment")
        session = StringSession(session_string)
    else:
        print("🔑 Using session file (session.session)")
        session = "session"
    
    client = TelegramClient(session, api_id, api_hash)
    
    with client:
        iteration = 0
        while True:
            iteration += 1
            start_time = time.time()
            
            # Calculate sliding 7-day window
            now = datetime.now(timezone.utc)
            since_date = now - timedelta(days=DAYS_BACK)
            
            print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Fetch #{iteration}")
            print(f"📅 Window: {since_date.date()} to {now.date()}")
            print("-" * 70)
            
            # Get all channels from database
            channels = Channel.objects.all().order_by('username')
            
            if not channels:
                print("⚠️  No channels in database")
            
            total_new = 0
            total_updated = 0
            for channel in channels:
                print(f"📺 Fetching {channel.username}...")
                new_posts, updated_posts = check_channel(client, channel, since_date)
                total_new += new_posts
                total_updated += updated_posts
                
                if new_posts > 0 or updated_posts > 0:
                    print(f"  📊 New: {new_posts}, Updated: {updated_posts}")
                else:
                    print(f"  ✓ No changes")
                
                # Rate limiting between channels
                time.sleep(RATE_LIMIT_DELAY)
            
            elapsed = time.time() - start_time
            print("-" * 70)
            print(f"✅ Fetch complete | New: {total_new} | Updated: {total_updated} | Time: {elapsed:.1f}s")
            
            # Wait for next check
            sleep_time = max(0, CHECK_INTERVAL - elapsed)
            if sleep_time > 0:
                print(f"😴 Sleeping for {sleep_time:.0f}s until next fetch...")
                time.sleep(sleep_time)


if __name__ == "__main__":
    try:
        fetch_loop()
    except KeyboardInterrupt:
        print("\n\n👋 Fetch service stopped")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

