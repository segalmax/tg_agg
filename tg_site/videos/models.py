from django.db import models


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

    class Meta:
        unique_together = [['channel', 'telegram_id']]
        ordering = ['-date']

    def __str__(self):
        return f"{self.channel.username} - {self.telegram_id}"
