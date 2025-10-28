#!/usr/bin/env python3
"""
backfill_posts.py
-----------------
Fetch and upsert Telegram posts into the local Django database.

Usage examples:

    # Fetch all posts since 2024-01-01 and stop after first existing post
    python backfill_posts.py --channel abualiexpress \
                             --since 2024-01-01 \
                             --only-newer-than-db

    # Fetch entire history and upsert/update everything in DB
    python backfill_posts.py --channel abualiexpress --since 2015-01-01

Requirements:
  * A valid `session.session` file in project root (Telethon session)
  * Django settings configured via `.env` (DATABASE, SECRET_KEY, etc.)
  * `telethon`, `django`, and `pymysql` installed in the active venv
"""
import os
import sys
import argparse
from datetime import datetime, timezone
import time

from typing import Optional

# --- Django setup ---------------------------------------------------------
PROJECT_DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(PROJECT_DIR, "tg_site"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()

from videos.models import Channel, Post  # noqa: E402
from telethon.sync import TelegramClient  # noqa: E402
from telethon.tl.types import Message  # noqa: E402

# -------------------------------------------------------------------------
CHUNK_SIZE = 200  # messages per API request
SLEEP_SECONDS = 1  # polite delay between chunks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill Telegram posts into Django DB")
    parser.add_argument("--channel", required=True, help="Channel username (without @)")
    parser.add_argument("--since", required=True, help="Fetch posts newer than this YYYY-MM-DD date")
    parser.add_argument(
        "--only-newer-than-db",
        action="store_true",
        help="Stop as soon as we encounter first post that already exists in DB",
    )
    parser.add_argument("--api-id", type=int, help="Telegram API ID (optional, fallback to ENV)")
    parser.add_argument("--api-hash", help="Telegram API HASH (optional, fallback to ENV)")
    return parser.parse_args()


def ensure_channel(channel_username: str) -> Channel:
    channel, _ = Channel.objects.get_or_create(
        username=channel_username, defaults={"title": channel_username}
    )
    return channel


def save_message(msg: Message, channel: Channel) -> bool:
    """Upsert Telethon message -> Post; return True if inserted, False if updated"""
    media_type = None
    video_data = None
    has_media = bool(msg.media)

    if msg.media:
        media_type = type(msg.media).__name__
        # basic video metadata
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


def backfill(channel_username: str, since_date: datetime, stop_on_existing: bool):
    channel = ensure_channel(channel_username)

    api_id = int(os.getenv("API_ID", "0"))
    api_hash = os.getenv("API_HASH", "")

    if api_id == 0 or not api_hash:
        print("❌ API_ID / API_HASH not set (env vars). Provide via env or args.")
        sys.exit(1)

    print(
        f"🚀 Backfilling posts for @{channel_username} since {since_date.date()} (stop_on_existing={stop_on_existing})"
    )

    client = TelegramClient("session", api_id, api_hash)
    with client:
        entity = client.get_entity(channel_username)
        offset_id: Optional[int] = 0
        total_new = 0
        total_checked = 0
        while True:
            msgs = client.get_messages(entity, limit=CHUNK_SIZE, max_id=offset_id)
            if not msgs:
                break

            for msg in msgs:
                total_checked += 1
                if msg.date.replace(tzinfo=timezone.utc) < since_date:
                    print("✓ Reached messages older than since_date. Stopping.")
                    return
                created = save_message(msg, channel)
                if created:
                    total_new += 1
                    text_preview = (msg.text or "")[:40]
                    print(f" + {msg.id} | {msg.date.date()} | {text_preview}")
                elif stop_on_existing:
                    print("✓ Encountered first existing post. Stopping.")
                    return
            offset_id = msgs[-1].id
            time.sleep(SLEEP_SECONDS)

        print(f"✅ Done. New posts inserted: {total_new}, total checked: {total_checked}")


if __name__ == "__main__":
    ns = parse_args()
    try:
        since_dt = datetime.fromisoformat(ns.since).replace(tzinfo=timezone.utc)
    except ValueError:
        print("❌ --since must be YYYY-MM-DD")
        sys.exit(1)

    if ns.api_id:
        os.environ["API_ID"] = str(ns.api_id)
    if ns.api_hash:
        os.environ["API_HASH"] = ns.api_hash

    backfill(ns.channel, since_dt, ns.only_newer_than_db)
