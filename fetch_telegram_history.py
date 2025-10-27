#!/usr/bin/env python3
"""
Fetch messages from Telegram channel month-by-month using official Telegram API
"""
import json
from datetime import datetime, timedelta
from telethon import TelegramClient
import asyncio
import os

# Telegram API credentials
API_ID = 25486530
API_HASH = '178cf13588f57714d72abed67409221a'
PHONE = '+972509909987'

# Channel to fetch
CHANNEL_USERNAME = 'danielamram3'

# How many months back to fetch (Oct 2023 to Oct 2025 = 25 months)
MONTHS_BACK = 25

# Output directory
OUTPUT_DIR = f'{CHANNEL_USERNAME}_monthly'

def generate_month_ranges(months_back):
    """Generate list of (start_date, end_date, month_label) tuples"""
    from datetime import timezone
    ranges = []
    now = datetime.now(timezone.utc)
    
    for i in range(months_back):
        # Calculate start of month
        if i == 0:
            # Current month - from start of month to now
            end_date = now
            start_date = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        else:
            # Previous months - full month
            month_offset = now.month - i
            year_offset = now.year
            while month_offset <= 0:
                month_offset += 12
                year_offset -= 1
            
            start_date = datetime(year_offset, month_offset, 1, tzinfo=timezone.utc)
            
            # End date is start of next month minus 1 second
            if month_offset == 12:
                end_date = datetime(year_offset + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
            else:
                end_date = datetime(year_offset, month_offset + 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
        
        month_label = start_date.strftime('%Y_%m')
        ranges.append((start_date, end_date, month_label))
    
    return ranges

async def main():
    if not API_ID or not API_HASH:
        print("❌ ERROR: You need to set API_ID and API_HASH!")
        print("Go to https://my.telegram.org and get your credentials")
        return
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Create client
    client = TelegramClient('session', API_ID, API_HASH)
    
    try:
        await client.start(phone=PHONE)
        print(f"✓ Connected to Telegram as {PHONE}")
        
        # Get channel entity
        channel = await client.get_entity(CHANNEL_USERNAME)
        print(f"✓ Found channel: {channel.title}\n")
        
        # Generate month ranges
        month_ranges = generate_month_ranges(MONTHS_BACK)
        
        total_messages = 0
        total_videos = 0
        
        print(f"📊 Will fetch {len(month_ranges)} months of data\n")
        
        for idx, (start_date, end_date, month_label) in enumerate(month_ranges, 1):
            output_file = f"{OUTPUT_DIR}/{CHANNEL_USERNAME}_{month_label}.json"
            
            # Skip if already exists
            if os.path.exists(output_file):
                print(f"⏭  Skipping {month_label} (already exists)")
                continue
            
            print(f"📅 [{idx}/{len(month_ranges)}] Fetching {month_label} ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})...")
            
            messages = []
            count = 0
            video_count_temp = 0
            
            async for message in client.iter_messages(channel, offset_date=end_date, reverse=False):
                # Stop when we reach messages before start_date
                if message.date < start_date:
                    print(f"  Reached start date boundary at message {count}")
                    break
                
                count += 1
                if count % 50 == 0:
                    print(f"  Fetched {count} messages ({video_count_temp} videos so far)...")
                
                # Extract message data with all available metadata
                msg_data = {
                    'id': message.id,
                    'date': int(message.date.timestamp()) if message.date else None,
                    'date_str': message.date.isoformat() if message.date else None,
                    'text': message.text or '',
                    'views': message.views or 0,
                    'forwards': message.forwards or 0,
                    'replies': message.replies.replies if message.replies else 0,
                    'link': f'https://t.me/{CHANNEL_USERNAME}/{message.id}',
                    'has_media': bool(message.media),
                    'media_type': type(message.media).__name__ if message.media else None,
                    'edit_date': int(message.edit_date.timestamp()) if message.edit_date else None,
                    'pinned': message.pinned,
                    'grouped_id': message.grouped_id,
                    'post_author': message.post_author,
                }
                
                # Add reactions if present
                if message.reactions:
                    msg_data['reactions'] = []
                    for reaction in message.reactions.results:
                        msg_data['reactions'].append({
                            'emoji': reaction.reaction.emoticon if hasattr(reaction.reaction, 'emoticon') else str(reaction.reaction),
                            'count': reaction.count
                        })
                
                # Extract video info if present
                if message.video:
                    msg_data['video'] = {
                        'duration': getattr(message.video, 'duration', None),
                        'width': getattr(message.video, 'w', None),
                        'height': getattr(message.video, 'h', None),
                        'size': getattr(message.video, 'size', None),
                    }
                    video_count_temp += 1
                elif message.document and message.document.mime_type and 'video' in message.document.mime_type:
                    msg_data['video'] = {
                        'duration': None,
                        'size': message.document.size,
                    }
                    video_count_temp += 1
                
                messages.append(msg_data)
            
            if not messages:
                print(f"  No messages found for {month_label}")
                continue
            
            # Save to JSON file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
            
            video_count = sum(1 for m in messages if 'video' in m)
            total_messages += len(messages)
            total_videos += video_count
            
            print(f"  ✓ Saved {len(messages)} messages ({video_count} videos) to {output_file}")
        
        print(f"\n=== FINAL STATS ===")
        print(f"Total messages: {total_messages:,}")
        print(f"Total videos: {total_videos:,}")
        print(f"Files saved in: {OUTPUT_DIR}/")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user - saving progress...")
        print(f"✓ Session saved. Re-run to continue from where you left off.")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        raise
    finally:
        # Always disconnect cleanly
        if client.is_connected():
            await client.disconnect()
            print("✓ Disconnected cleanly")

if __name__ == '__main__':
    asyncio.run(main())

