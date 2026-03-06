"""
Demo script showing semantic search capabilities.
Run after migration is complete.
"""

from videos.models import Post, Channel
from django.db.models import Q


def demo_basic_search():
    print("\n=== Basic Semantic Search ===")
    query = "artificial intelligence and machine learning"
    results = Post.semantic_search(query, limit=5)
    
    print(f"Query: '{query}'")
    print(f"Found {len(results)} results:\n")
    
    for i, post in enumerate(results, 1):
        print(f"{i}. @{post.channel.username} ({post.views} views)")
        print(f"   {post.text[:150]}...")
        print()


def demo_filtered_search():
    print("\n=== Semantic Search with Filters ===")
    query = "cryptocurrency bitcoin"
    results = Post.semantic_search(
        query, 
        limit=5,
        filters=Q(views__gte=1000) & Q(has_media=True)
    )
    
    print(f"Query: '{query}'")
    print(f"Filter: views >= 1000, has media")
    print(f"Found {len(results)} results:\n")
    
    for i, post in enumerate(results, 1):
        print(f"{i}. @{post.channel.username} ({post.views} views, {post.media_type})")
        print(f"   {post.text[:150]}...")
        print()


def demo_hybrid_search():
    print("\n=== Hybrid Search (Keyword + Semantic) ===")
    query = "technology startup"
    results = Post.hybrid_search(query, limit=5)
    
    print(f"Query: '{query}'")
    print(f"Found {len(results)} results:\n")
    
    for i, post in enumerate(results, 1):
        print(f"{i}. @{post.channel.username}")
        print(f"   {post.text[:150]}...")
        print()


def demo_channel_specific_search():
    print("\n=== Semantic Search in Specific Channel ===")
    
    channels = Channel.objects.all()[:3]
    if not channels:
        print("No channels found")
        return
    
    channel = channels[0]
    query = "news update"
    
    results = Post.semantic_search(
        query,
        limit=5,
        filters=Q(channel=channel)
    )
    
    print(f"Query: '{query}'")
    print(f"Channel: @{channel.username}")
    print(f"Found {len(results)} results:\n")
    
    for i, post in enumerate(results, 1):
        print(f"{i}. {post.date.strftime('%Y-%m-%d')}")
        print(f"   {post.text[:150]}...")
        print()


def compare_search_methods():
    print("\n=== Comparing Search Methods ===")
    query = "investing money finance"
    
    print(f"Query: '{query}'\n")
    
    # Traditional keyword search
    keyword_results = Post.objects.filter(text__icontains=query.split()[0])[:5]
    print(f"1. Keyword search ('{query.split()[0]}' in text):")
    for post in keyword_results:
        print(f"   - {post.text[:100]}...")
    
    # Semantic search
    semantic_results = Post.semantic_search(query, limit=5)
    print(f"\n2. Semantic search (meaning similarity):")
    for post in semantic_results:
        print(f"   - {post.text[:100]}...")
    
    print("\nNotice: Semantic search finds related concepts, not just exact words!")


def show_embedding_stats():
    print("\n=== Embedding Statistics ===")
    total_posts = Post.objects.count()
    posts_with_embeddings = Post.objects.filter(embedding__isnull=False).count()
    posts_without_embeddings = total_posts - posts_with_embeddings
    
    print(f"Total posts: {total_posts}")
    print(f"Posts with embeddings: {posts_with_embeddings}")
    print(f"Posts without embeddings: {posts_without_embeddings}")
    print(f"Coverage: {posts_with_embeddings/total_posts*100:.1f}%")
    
    if posts_without_embeddings > 0:
        print(f"\nRun: python manage.py generate_embeddings")


if __name__ == "__main__":
    print("=" * 60)
    print("SEMANTIC SEARCH DEMO")
    print("=" * 60)
    
    show_embedding_stats()
    
    if Post.objects.filter(embedding__isnull=False).exists():
        demo_basic_search()
        demo_filtered_search()
        demo_hybrid_search()
        demo_channel_specific_search()
        compare_search_methods()
        
        print("\n" + "=" * 60)
        print("Demo complete!")
        print("=" * 60)
    else:
        print("\nNo embeddings found. Run: python manage.py generate_embeddings")

