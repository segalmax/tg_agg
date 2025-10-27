from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('channel/<str:username>/', views.channel_posts, name='channel_posts'),
    path('api/video/<str:channel>/<int:post_id>/', views.get_video_url, name='get_video_url'),
]

