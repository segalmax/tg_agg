from django.db import models
from pgvector.django import VectorField
from sentence_transformers import SentenceTransformer
import numpy as np


class EmbeddingGenerator:
    _model = None
    
    @classmethod
    def get_model(cls):
        if cls._model is None:
            cls._model = SentenceTransformer('all-MiniLM-L6-v2')
        return cls._model
    
    @classmethod
    def generate_embedding(cls, text):
        if not text or not text.strip():
            return None
        model = cls.get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()


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
    text = models.TextField(db_index=True)
    views = models.IntegerField(default=0)
    forwards = models.IntegerField(default=0)
    replies = models.IntegerField(default=0)
    link = models.URLField()
    has_media = models.BooleanField(default=False)
    media_type = models.CharField(max_length=50, null=True, blank=True)
    video_data = models.JSONField(null=True, blank=True)
    when_added = models.DateTimeField(auto_now_add=True)
    when_updated = models.DateTimeField(null=True, blank=True)
    embedding = VectorField(dimensions=384, null=True, blank=True)

    class Meta:
        unique_together = [['channel', 'telegram_id']]
        ordering = ['-date']

    def __str__(self):
        return f"{self.channel.username} - {self.telegram_id}"
    
    def save(self, *args, **kwargs):
        if self.text and not self.embedding:
            self.embedding = EmbeddingGenerator.generate_embedding(self.text)
        super().save(*args, **kwargs)
    
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
            models.RawSQL('embedding <=> %s', (query_embedding,))
        )[:limit]
        
        return queryset
    
    @classmethod
    def hybrid_search(cls, query_text, limit=10, keyword_weight=0.3, semantic_weight=0.7):
        """
        Combine keyword search (traditional) with semantic search.
        
        Learning: This shows how to blend old and new approaches.
        """
        from django.db.models import Q, Value, FloatField
        
        keyword_results = cls.objects.filter(
            Q(text__icontains=query_text)
        ).annotate(
            keyword_score=Value(keyword_weight, output_field=FloatField())
        )
        
        semantic_results = cls.semantic_search(query_text, limit=limit*2)
        
        combined_ids = set()
        combined = []
        
        for post in semantic_results:
            combined_ids.add(post.id)
            combined.append(post)
            if len(combined) >= limit:
                break
        
        for post in keyword_results:
            if post.id not in combined_ids:
                combined.append(post)
                combined_ids.add(post.id)
            if len(combined) >= limit:
                break
        
        return combined[:limit]

