from django.db import models
from django.db.models.expressions import RawSQL
from pgvector.django import VectorField
from openai import OpenAI
import tiktoken
import os


class EmbeddingGenerator:
    _client = None
    _encoding = None
    
    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        return cls._client
    
    @classmethod
    def get_encoding(cls):
        if cls._encoding is None:
            cls._encoding = tiktoken.encoding_for_model("text-embedding-3-small")
        return cls._encoding
    
    @classmethod
    def generate_embedding(cls, text):
        if not text or not text.strip():
            return None
        
        # Properly truncate by tokens, not characters
        encoding = cls.get_encoding()
        tokens = encoding.encode(text)
        if len(tokens) > 8191:
            tokens = tokens[:8191]
            text = encoding.decode(tokens)
        
        client = cls.get_client()
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    @classmethod
    def generate_embeddings_batch(cls, texts):
        """Generate embeddings for multiple texts in a single API call"""
        if not texts:
            return []
        
        # Truncate each text properly
        encoding = cls.get_encoding()
        processed_texts = []
        for text in texts:
            if not text or not text.strip():
                processed_texts.append("")
            else:
                tokens = encoding.encode(text)
                if len(tokens) > 8191:
                    tokens = tokens[:8191]
                    text = encoding.decode(tokens)
                processed_texts.append(text)
        
        client = cls.get_client()
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=processed_texts
        )
        return [item.embedding for item in response.data]


class Channel(models.Model):
    username = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username


class Post(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    telegram_id = models.IntegerField()
    date = models.DateTimeField(db_index=True)
    text = models.TextField()
    views = models.IntegerField(default=0)
    forwards = models.IntegerField(default=0)
    replies = models.IntegerField(default=0)
    link = models.URLField()
    has_media = models.BooleanField(default=False)
    media_type = models.CharField(max_length=50, null=True, blank=True)
    video_data = models.JSONField(null=True, blank=True)
    when_added = models.DateTimeField(auto_now_add=True)
    when_updated = models.DateTimeField(null=True, blank=True)
    embedding = VectorField(dimensions=1536, null=True, blank=True)

    class Meta:
        unique_together = [['channel', 'telegram_id']]
        ordering = ['-date']

    def __str__(self):
        return f"{self.channel.username} - {self.telegram_id}"

    def weighted_engagement_score(self):
        """Same raw signal as Popular / Trending numerator: views + forwards×30 + replies×5."""
        return self.views + self.forwards * 30 + self.replies * 5

    def viral_ratio(self):
        """Same as sort -viral: forwards ÷ (views + 1)."""
        return float(self.forwards) / (float(self.views) + 1.0)

    @classmethod
    def semantic_search(cls, query_text, limit=10, filters=None):
        """
        Perform semantic search on posts.
        
        Args:
            query_text: Text to search for
            limit: Max results to return
            filters: Optional Q object for additional filtering
        
        Returns:
            QuerySet of Posts ordered by similarity
        """
        query_embedding = EmbeddingGenerator.generate_embedding(query_text)
        if not query_embedding:
            return cls.objects.none()
        
        queryset = cls.objects.filter(embedding__isnull=False)
        if filters:
            queryset = queryset.filter(filters)
        
        queryset = queryset.order_by(
            RawSQL('embedding <=> %s::vector', (str(query_embedding),))
        )[:limit]
        
        return queryset
    
    @classmethod
    def hybrid_search(cls, query_text, keyword_filters=None, limit=10):
        """
        Combine keyword search (traditional) with semantic search.
        Returns a queryset-like list prioritizing semantic results.
        
        Learning: This shows how to blend old and new approaches.
        """
        
        # Get semantic results (highest priority)
        semantic_results = list(cls.semantic_search(query_text, limit=limit*2))
        
        # Get keyword results
        if keyword_filters:
            keyword_results = list(cls.objects.filter(keyword_filters).distinct()[:limit*2])
        else:
            keyword_results = []
        
        # Combine: prioritize semantic, then add keyword results not in semantic
        combined_ids = set()
        combined = []
        
        # Add semantic results first
        for post in semantic_results:
            combined_ids.add(post.id)
            combined.append(post)
        
        # Add keyword results that aren't already in semantic results
        for post in keyword_results:
            if post.id not in combined_ids:
                combined.append(post)
                combined_ids.add(post.id)
        
        # Return as queryset by getting IDs and doing a single query
        if not combined:
            return cls.objects.none()
        
        post_ids = [p.id for p in combined[:limit*3]]  # Get more for filtering
        return cls.objects.filter(id__in=post_ids)

