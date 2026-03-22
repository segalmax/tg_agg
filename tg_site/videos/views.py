from datetime import timedelta

from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import ExpressionWrapper, FloatField, F
from django.db.models.expressions import RawSQL
from .models import Channel, Post
import urllib.request
import re

DEFAULT_SORT = '-trending'


ALLOWED_SORTS = [
    'date', '-date', 'views', '-views',
    'forwards', '-forwards', 'replies', '-replies',
    '-popular', '-trending', '-viral',
]


def apply_sort(posts, sort_by):
    if sort_by == '-popular':
        return posts.annotate(popularity=ExpressionWrapper(
            F('views') + F('forwards') * 30 + F('replies') * 5,
            output_field=FloatField()
        )).order_by('-popularity')
    elif sort_by == '-trending':
        return posts.annotate(trending_score=RawSQL(
            "(views + forwards*30 + replies*5)::float / POWER(EXTRACT(EPOCH FROM (NOW() - date))/3600.0 + 2, 1.5)",
            []
        )).order_by('-trending_score')
    elif sort_by == '-viral':
        return posts.annotate(viral_score=ExpressionWrapper(
            F('forwards') * 1.0 / (F('views') + 1),
            output_field=FloatField()
        )).order_by('-viral_score')
    return posts.order_by(sort_by)


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
    
    # Date range (inclusive). Default when GET omits both keys: from = 7 days ago, no default "to" (open-ended).
    today = timezone.localdate()
    default_date_from = (today - timedelta(days=7)).isoformat()
    implicit_date_range = 'date_from' not in request.GET and 'date_to' not in request.GET
    if implicit_date_range:
        date_from_effective = default_date_from
        date_to_effective = ''
        additional_filters &= Q(date__date__gte=date_from_effective)
    else:
        date_from_effective = request.GET.get('date_from', '').strip()
        date_to_effective = request.GET.get('date_to', '').strip()
        if date_from_effective:
            additional_filters &= Q(date__date__gte=date_from_effective)
        if date_to_effective:
            additional_filters &= Q(date__date__lte=date_to_effective)
    
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
    
    implicit_sort = 'sort' not in request.GET
    # Pure semantic (keywords off): keep embedding relevance order. Keywords or hybrid: honor sort.
    semantic_only = search_semantic and not search_keywords
    if not semantic_only:
        sort_by = request.GET.get('sort', DEFAULT_SORT)
        if sort_by in ALLOWED_SORTS:
            posts = apply_sort(posts, sort_by)
    
    # Get all channels for filter dropdown
    channels = Channel.objects.all().order_by('username')
    
    paginator = Paginator(posts, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Build query params for pagination (merge implicit defaults so page links keep state)
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')
    if implicit_date_range:
        query_params['date_from'] = date_from_effective
    if implicit_sort:
        query_params['sort'] = DEFAULT_SORT
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
            'date_from': date_from_effective if implicit_date_range else (request.GET.get('date_from', '').strip()),
            'date_to': date_to_effective if implicit_date_range else (request.GET.get('date_to', '').strip()),
            'default_date_from': default_date_from,
            'default_date_to': '',
            'sort': request.GET.get('sort', DEFAULT_SORT),
        }
    })


def channel_posts(request, username):
    channel = get_object_or_404(Channel, username=username)
    posts = Post.objects.filter(channel=channel)
    
    paginator = Paginator(posts, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    today = timezone.localdate()
    channels = Channel.objects.all().order_by('username')
    return render(request, 'videos/post_list.html', {
        'page_obj': page_obj,
        'channel': channel,
        'channels': channels,
        'search_query': '',
        'query_string': '',
        'total_count': posts.count(),
        'filters': {
            'channels': '',
            'media': 'video',
            'date_from': '',
            'date_to': '',
            'default_date_from': (today - timedelta(days=7)).isoformat(),
            'default_date_to': '',
            'sort': DEFAULT_SORT,
        },
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
    
    sort_by = request.GET.get('sort', DEFAULT_SORT)
    if sort_by in ALLOWED_SORTS:
        posts = apply_sort(posts, sort_by)

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


def fetch_embed_html(channel, msg_id, single=False):
    url = f"https://t.me/{channel}/{msg_id}?embed=1"
    if single:
        url += "&single=1"
    req = urllib.request.Request(url, headers=TELEGRAM_HEADERS)
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
    """Fetch media URL(s) from Telegram embed page. Handles videos and photos.
    Optional ?message_id=X: fetch single-message embed; if no video found, return type=none."""
    try:
        message_id_param = request.GET.get('message_id')
        want_photo = request.GET.get('media_type') == 'photo'

        msg_id = message_id_param or post_id
        html = fetch_embed_html(channel, msg_id, single=bool(message_id_param))
        thumbnail = extract_thumbnail(html)

        if not want_photo:
            videos = extract_all_mp4s(html)
            if videos:
                return JsonResponse({'type': 'video', 'thumbnail': thumbnail, 'video': videos[0], 'videos': videos if not message_id_param else [videos[0]]})

        photos = extract_all_photos(html)
        if photos:
            return JsonResponse({'type': 'photo', 'thumbnail': photos[0], 'photo': photos[0], 'photos': photos if not message_id_param else [photos[0]]})

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
        Channel.objects.create(username=username, title=username)
        
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
