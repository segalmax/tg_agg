#!/usr/bin/env python3
"""
One-time script: merge existing album posts in the DB.
Finds consecutive-ID video posts with identical timestamps and merges them:
  - primary post gets video_data.album_ids = [id1, id2, ...]
  - secondary posts are deleted
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tg_site'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db import connection


def find_albums():
    with connection.cursor() as cur:
        cur.execute("""
            SELECT channel_id, date, array_agg(telegram_id ORDER BY telegram_id) as ids
            FROM videos_post
            WHERE video_data IS NOT NULL
            GROUP BY channel_id, date
            HAVING count(*) > 1
              AND max(telegram_id) - min(telegram_id) = count(*) - 1
            ORDER BY date DESC
        """)
        return cur.fetchall()


def merge_album(channel_id, album_ids):
    primary_id = album_ids[0]
    secondary_ids = album_ids[1:]

    with connection.cursor() as cur:
        cur.execute("""
            UPDATE videos_post
            SET video_data = video_data || %s::jsonb
            WHERE channel_id = %s AND telegram_id = %s
        """, [f'{{"album_ids": {list(album_ids)}}}', channel_id, primary_id])

        cur.execute("""
            DELETE FROM videos_post
            WHERE channel_id = %s AND telegram_id = ANY(%s)
        """, [channel_id, list(secondary_ids)])

    return len(secondary_ids)


def main():
    albums = find_albums()
    print(f"Found {len(albums)} album groups to merge")

    total_deleted = 0
    for channel_id, date, album_ids in albums:
        deleted = merge_album(channel_id, album_ids)
        total_deleted += deleted
        print(f"  channel={channel_id} date={date} ids={album_ids} → deleted {deleted} secondary posts")

    print(f"\nDone. Merged {len(albums)} albums, deleted {total_deleted} secondary posts.")


if __name__ == '__main__':
    main()
