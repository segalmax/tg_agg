from django.contrib import admin
from .models import Channel, Post


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ['username', 'title', 'created_at']
    search_fields = ['username', 'title']


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['telegram_id', 'channel', 'date', 'text_preview', 'views', 'has_media']
    list_filter = ['channel', 'has_media', 'date']
    search_fields = ['text']
    date_hierarchy = 'date'
    
    def text_preview(self, obj):
        return obj.text[:100] if obj.text else ''
