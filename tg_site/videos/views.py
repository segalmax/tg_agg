from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Channel, Post
import requests
import re


def home(request):
    posts = Post.objects.select_related('channel').all()
    
    # Filters
    search_query = request.GET.get('q', '').strip()
    if search_query:
        posts = posts.filter(text__icontains=search_query)
    
    channel_filter = request.GET.get('channel', '').strip()
    if channel_filter:
        posts = posts.filter(channel__username=channel_filter)
    
    media_filter = request.GET.get('media', '').strip()
    if not media_filter:
        media_filter = 'video'
    
    if media_filter == 'video':
        posts = posts.filter(video_data__isnull=False)
    elif media_filter == 'photo':
        posts = posts.filter(media_type='MessageMediaPhoto')
    elif media_filter == 'all_media':
        posts = posts.filter(has_media=True)
    
    min_views = request.GET.get('min_views', '').strip()
    if min_views:
        try:
            posts = posts.filter(views__gte=int(min_views))
        except ValueError:
            pass
    
    date_from = request.GET.get('date_from', '').strip()
    if date_from:
        posts = posts.filter(date__gte=date_from)
    
    date_to = request.GET.get('date_to', '').strip()
    if date_to:
        posts = posts.filter(date__lte=date_to)
    
    # Sorting
    sort_by = request.GET.get('sort', '-date')
    if sort_by in ['date', '-date', 'views', '-views', 'forwards', '-forwards', 'replies', '-replies']:
        posts = posts.order_by(sort_by)
    
    # Get all channels for filter dropdown
    channels = Channel.objects.all().order_by('username')
    
    paginator = Paginator(posts, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Build query params for pagination
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    query_string = '&' + query_params.urlencode() if query_params else ''
    
    return render(request, 'videos/post_list.html', {
        'page_obj': page_obj,
        'search_query': search_query or '',
        'channels': channels,
        'query_string': query_string,
        'filters': {
            'channel': channel_filter or '',
            'media': media_filter or '',
            'min_views': min_views or '',
            'date_from': date_from or '',
            'date_to': date_to or '',
            'sort': sort_by or '-date',
        }
    })


def channel_posts(request, username):
    channel = get_object_or_404(Channel, username=username)
    posts = Post.objects.filter(channel=channel)
    
    paginator = Paginator(posts, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'videos/post_list.html', {
        'page_obj': page_obj,
        'channel': channel,
    })


def get_video_url(request, channel, post_id):
    """Fetch video URL from Telegram embed page"""
    try:
        embed_url = f"https://t.me/{channel}/{post_id}?embed=1"
        resp = requests.get(embed_url, timeout=10)
        
        # Extract thumbnail
        thumb_match = re.search(r"background-image:url\('([^']+)'\)", resp.text)
        thumbnail = thumb_match.group(1) if thumb_match else None
        
        # Extract video source - look for .mp4 URLs
        video_url = None
        # Primary regex for direct mp4 links
        primary = re.search(r'(https://[^"\']+\.mp4[^"\'\s]*)', resp.text)
        if primary:
            video_url = primary.group(1)
        else:
            # Fallback: look for <source src="...mp4">
            source_tag = re.search(r'<source[^>]+src="([^"\s]*\.mp4[^"\s]*)"', resp.text)
            if source_tag:
                video_url = source_tag.group(1)
            else:
                # Fallback: look for <video src="...mp4">
                video_inline = re.search(r'<video[^>]+src="([^"\s]*\.mp4[^"\s]*)"', resp.text)
                if video_inline:
                    video_url = video_inline.group(1)
        
        print(f"Video fetch for {channel}/{post_id}: video={bool(video_url)}, thumb={bool(thumbnail)}")
        
        return JsonResponse({
            'thumbnail': thumbnail,
            'video': video_url
        })
    except Exception as e:
        print(f"Error fetching video {channel}/{post_id}: {str(e)}")
        return JsonResponse({'error': 'Failed to fetch video'}, status=500)
