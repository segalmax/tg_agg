from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import Channel, Post
import requests
import re
import os


def home(request):
    posts = Post.objects.select_related('channel').all()
    
    # Filters
    search_query = request.GET.get('q', '').strip()
    if search_query:
        posts = posts.filter(text__icontains=search_query)
    
    # Multi-channel filter (comma-separated)
    channel_filter = request.GET.get('channels', '').strip()
    if channel_filter:
        channel_list = [c.strip() for c in channel_filter.split(',') if c.strip()]
        if channel_list:
            posts = posts.filter(channel__username__in=channel_list)
    
    # Media filter - now defaults to 'video' for backwards compatibility
    media_filter = request.GET.get('media', 'video').strip()
    
    if media_filter == 'video':
        posts = posts.filter(video_data__isnull=False)
    elif media_filter == 'photo':
        posts = posts.filter(media_type='MessageMediaPhoto')
    elif media_filter == 'has_media':
        posts = posts.filter(has_media=True)
    # 'all' = no filtering, show everything
    
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
    
    # Count total posts matching filters
    total_count = posts.count()
    
    return render(request, 'videos/post_list.html', {
        'page_obj': page_obj,
        'search_query': search_query or '',
        'channels': channels,
        'query_string': query_string,
        'total_count': total_count,
        'filters': {
            'channels': channel_filter or '',
            'media': media_filter or 'video',
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


def post_detail(request, username, post_id):
    """Display single post with navigation to prev/next posts"""
    channel = get_object_or_404(Channel, username=username)
    post = get_object_or_404(Post, channel=channel, telegram_id=post_id)
    
    # Get filters from query params to maintain context
    posts = Post.objects.select_related('channel').all()
    
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
    
    date_from = request.GET.get('date_from', '').strip()
    if date_from:
        posts = posts.filter(date__gte=date_from)
    
    date_to = request.GET.get('date_to', '').strip()
    if date_to:
        posts = posts.filter(date__lte=date_to)
    
    sort_by = request.GET.get('sort', '-date')
    if sort_by in ['date', '-date', 'views', '-views', 'forwards', '-forwards', 'replies', '-replies']:
        posts = posts.order_by(sort_by)
    
    # Find prev/next in filtered list
    posts_list = list(posts.values_list('channel__username', 'telegram_id', flat=False))
    current_idx = None
    for idx, (ch_user, tid) in enumerate(posts_list):
        if ch_user == username and tid == post_id:
            current_idx = idx
            break
    
    prev_post = None
    next_post = None
    if current_idx is not None:
        if current_idx > 0:
            prev_post = posts_list[current_idx - 1]
        if current_idx < len(posts_list) - 1:
            next_post = posts_list[current_idx + 1]
    
    # Build query string for navigation
    query_params = request.GET.copy()
    query_string = '&' + query_params.urlencode() if query_params else ''
    
    return render(request, 'videos/post_detail.html', {
        'post': post,
        'prev_post': prev_post,
        'next_post': next_post,
        'query_string': query_string,
    })


def get_video_url(request, channel, post_id):
    """Fetch video URL from Telegram embed page"""
    try:
        embed_url = f"https://t.me/{channel}/{post_id}?embed=1"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(embed_url, timeout=10, headers=headers)
        
        # Extract thumbnail
        thumb_patterns = [
            r"background-image:url\('([^']+)'\)",
            r'poster["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'thumb["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        ]
        thumbnail = None
        for pattern in thumb_patterns:
            match = re.search(pattern, resp.text)
            if match:
                thumbnail = match.group(1)
                if thumbnail.startswith('//'):
                    thumbnail = 'https:' + thumbnail
                break
        
        # Extract video source - comprehensive patterns
        video_url = None
        
        patterns = [
            # Most specific first - direct video tag with src
            r'<video\s+[^>]*?src="([^"]+\.mp4[^"]*)"',
            r"<video\s+[^>]*?src='([^']+\.mp4[^']*)'",
            
            # JSON-style properties
            r'"file"\s*:\s*"([^"]+\.mp4[^"]*)"',
            r'"video"\s*:\s*"([^"]+\.mp4[^"]*)"',
            r'"url"\s*:\s*"([^"]+\.mp4[^"]*)"',
            r'"src"\s*:\s*"([^"]+\.mp4[^"]*)"',
            
            # HTML attributes (less specific)
            r'<source[^>]+src\s*=\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            r'src\s*=\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            
            # JavaScript variable assignments
            r'videoSrc\s*=\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            r'video_src\s*=\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            
            # Direct URL patterns (broad, last resort)
            r'(https?://[^\s"\'<>]+video[^\s"\'<>]*\.mp4[^\s"\'<>]*)',
            r'(//[^\s"\'<>]+telegram[^\s"\'<>]*\.mp4[^\s"\'<>]*)',
            r'(https?://[^\s"\'<>]+\.mp4(?:\?[^\s"\'<>]*)?)',
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, resp.text, re.IGNORECASE)
            if match:
                video_url = match.group(1)
                # Fix protocol-relative URLs
                if video_url.startswith('//'):
                    video_url = 'https:' + video_url
                # Unescape if needed
                video_url = video_url.replace('\\/', '/')
                print(f"Video fetch OK for {channel}/{post_id} (pattern #{i+1}): {video_url[:80]}")
                break
        
        if not video_url:
            # Debug: check if 'cdn' or 'telesco.pe' exist in response
            has_cdn = 'cdn' in resp.text.lower()
            has_telesco = 'telesco.pe' in resp.text
            has_mp4 = '.mp4' in resp.text
            print(f"Video fetch FAILED for {channel}/{post_id} - no video found (cdn={has_cdn}, telesco={has_telesco}, mp4={has_mp4}, len={len(resp.text)})")
        
        return JsonResponse({
            'thumbnail': thumbnail,
            'video': video_url
        })
    except Exception as e:
        print(f"Error fetching video {channel}/{post_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': 'Failed to fetch video'}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def add_channel(request):
    """Add a new channel by username - just insert into DB"""
    try:
        username = request.POST.get('username', '').strip().replace('@', '')
        
        if not username:
            return JsonResponse({'success': False, 'error': 'Username is required'}, status=400)
        
        # Check if channel already exists
        if Channel.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'error': 'Channel already exists'}, status=400)
        
        # Create channel with username as title (fetcher will update it later)
        channel = Channel.objects.create(username=username, title=username)
        
        return JsonResponse({
            'success': True,
            'message': f'Channel "@{username}" added successfully! Posts will appear within 1 minute.',
            'channel': {
                'username': username,
                'title': username
            }
        })
                
    except Exception as e:
        print(f"Error adding channel: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)
