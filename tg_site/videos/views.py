from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import Channel, Post
import requests
import urllib.request
import re
import os


def home(request):
    from django.db.models import Q
    
    # Build filter conditions first
    search_query = request.GET.get('q', '').strip()
    search_keywords = request.GET.get('search_keywords') == '1'
    search_semantic = request.GET.get('search_semantic') == '1'
    
    # Default to keywords if nothing is selected
    if not search_keywords and not search_semantic:
        search_keywords = True
    
    # Build additional filters
    additional_filters = Q()
    
    # Multi-channel filter
    channel_filter = request.GET.get('channels', '').strip()
    if channel_filter:
        channel_list = [c.strip() for c in channel_filter.split(',') if c.strip()]
        if channel_list:
            additional_filters &= Q(channel__username__in=channel_list)
    
    # Media filter
    media_filter = request.GET.get('media', 'video').strip()
    if media_filter == 'video':
        additional_filters &= Q(media_type='MessageMediaDocument')
    elif media_filter == 'photo':
        additional_filters &= Q(media_type='MessageMediaPhoto')
    elif media_filter == 'has_media':
        additional_filters &= Q(has_media=True)
    
    # Date range filters (inclusive on both ends)
    date_from = request.GET.get('date_from', '').strip()
    if date_from:
        additional_filters &= Q(date__date__gte=date_from)

    date_to = request.GET.get('date_to', '').strip()
    if date_to:
        additional_filters &= Q(date__date__lte=date_to)
    
    # Now apply search with all filters
    if search_query:
        if search_keywords and search_semantic:
            # Hybrid search: both semantic and keyword
            posts = Post.hybrid_search(
                query_text=search_query,
                keyword_filters=Q(text__icontains=search_query) & additional_filters,
                limit=1000
            )
        elif search_semantic:
            # Semantic search only
            posts = Post.semantic_search(
                query_text=search_query,
                filters=additional_filters,
                limit=1000
            )
        else:
            # Keywords search only (default)
            posts = Post.objects.select_related('channel').filter(
                Q(text__icontains=search_query) & additional_filters
            )
    else:
        # No search query - apply filters to all posts
        posts = Post.objects.select_related('channel').filter(additional_filters)
    
    # Sorting (skip for semantic/hybrid as they're already sorted by relevance)
    if not search_semantic:
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
    
    template = 'videos/grid_partial.html' if request.headers.get('HX-Request') else 'videos/post_list.html'
    return render(request, template, {
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
            'sort': request.GET.get('sort', '-date'),
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
        posts = posts.filter(date__date__gte=date_from)

    date_to = request.GET.get('date_to', '').strip()
    if date_to:
        posts = posts.filter(date__date__lte=date_to)
    
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


TELEGRAM_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'identity',
    'Referer': 'https://t.me/',
    'DNT': '1',
    'Connection': 'close',
}

THUMB_PATTERNS = [
    r"background-image:url\('([^']+)'\)",
    r'poster["\']?\s*[:=]\s*["\']([^"\']+)["\']',
    r'thumb["\']?\s*[:=]\s*["\']([^"\']+)["\']',
]


def fetch_embed_html(channel, msg_id):
    req = urllib.request.Request(f"https://t.me/{channel}/{msg_id}?embed=1", headers=TELEGRAM_HEADERS)
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.read().decode('utf-8')


def extract_all_mp4s(html):
    """Extract all unique MP4 URLs from HTML, deduplicating by filename."""
    seen = set()
    videos = []
    for raw_url in re.findall(r'(https?://[^\s"\'<>]+\.mp4(?:\?[^\s"\'<>]*)?)', html, re.IGNORECASE):
        url = raw_url.replace('\\/', '/')
        filename = url.split('/')[-1].split('?')[0]
        if filename not in seen:
            seen.add(filename)
            videos.append(url)
    return videos


def extract_thumbnail(html):
    for pattern in THUMB_PATTERNS:
        match = re.search(pattern, html)
        if match:
            url = match.group(1)
            return ('https:' + url) if url.startswith('//') else url
    return None


def extract_all_photos(html):
    """Extract Telegram CDN photo URLs from embed HTML, deduplicating by filename."""
    seen = set()
    photos = []
    for url in re.findall(r"background-image:url\('(https://cdn[^']+\.(?:jpg|jpeg|png|webp)[^']*)'\)", html):
        filename = url.split('/')[-1].split('?')[0]
        if filename not in seen:
            seen.add(filename)
            photos.append(url)
    return photos


def get_video_url(request, channel, post_id):
    """Fetch media URL(s) from Telegram embed page — handles both videos and photos."""
    try:
        html = fetch_embed_html(channel, post_id)
        thumbnail = extract_thumbnail(html)
        videos = extract_all_mp4s(html)
        if videos:
            print(f"Media fetch for {channel}/{post_id}: {len(videos)} video(s)")
            return JsonResponse({'type': 'video', 'thumbnail': thumbnail, 'video': videos[0], 'videos': videos})
        photos = extract_all_photos(html)
        if photos:
            print(f"Media fetch for {channel}/{post_id}: {len(photos)} photo(s)")
            return JsonResponse({'type': 'photo', 'thumbnail': photos[0], 'photo': photos[0], 'photos': photos})
        print(f"Media fetch for {channel}/{post_id}: nothing found")
        return JsonResponse({'type': 'none', 'thumbnail': thumbnail})
    except Exception as e:
        print(f"Error fetching media {channel}/{post_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)


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
