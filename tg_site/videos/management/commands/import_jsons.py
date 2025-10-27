import json
import glob
import os
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from videos.models import Channel, Post


class Command(BaseCommand):
    
    def handle(self, *args, **options):
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        pattern = os.path.join(base_path, '*_monthly', '*.json')
        json_files = glob.glob(pattern)
        
        total_posts = 0
        
        for json_file in json_files:
            folder_name = os.path.basename(os.path.dirname(json_file))
            channel_username = folder_name.replace('_monthly', '')
            
            channel, _ = Channel.objects.get_or_create(
                username=channel_username,
                defaults={'title': channel_username}
            )
            
            with open(json_file, 'r', encoding='utf-8') as f:
                posts_data = json.load(f)
            
            for post_data in posts_data:
                post_date = datetime.fromtimestamp(post_data['date'], tz=timezone.utc)
                
                Post.objects.update_or_create(
                    channel=channel,
                    telegram_id=post_data['id'],
                    defaults={
                        'date': post_date,
                        'text': post_data.get('text', ''),
                        'views': post_data.get('views', 0),
                        'forwards': post_data.get('forwards', 0),
                        'replies': post_data.get('replies', 0),
                        'link': post_data['link'],
                        'has_media': post_data.get('has_media', False),
                        'media_type': post_data.get('media_type'),
                        'video_data': post_data.get('video'),
                    }
                )
                total_posts += 1
            
            print(f"Imported {json_file}")
        
        print(f"Total posts imported: {total_posts}")

