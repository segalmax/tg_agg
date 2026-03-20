from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Channel, Post
from .views import apply_sort


def make_post(channel, telegram_id, *, views=0, forwards=0, replies=0, when=None):
    return Post.objects.create(
        channel=channel,
        telegram_id=telegram_id,
        date=when or timezone.now(),
        text='x',
        link='https://t.me/x/1',
        views=views,
        forwards=forwards,
        replies=replies,
    )


class ApplySortTests(TestCase):
    def setUp(self):
        self.channel = Channel.objects.create(username='sort_test_ch', title='sort_test_ch')

    def test_popular_orders_by_weighted_score(self):
        low = make_post(self.channel, 1, views=100, forwards=0, replies=0)
        high = make_post(self.channel, 2, views=50, forwards=2, replies=0)
        ordered = list(apply_sort(Post.objects.all(), '-popular'))
        self.assertEqual(ordered[0].pk, high.pk)
        self.assertEqual(ordered[1].pk, low.pk)

    def test_viral_orders_by_forwards_per_view(self):
        low = make_post(self.channel, 1, views=1000, forwards=1)
        high = make_post(self.channel, 2, views=10, forwards=5)
        ordered = list(apply_sort(Post.objects.all(), '-viral'))
        self.assertEqual(ordered[0].pk, high.pk)
        self.assertEqual(ordered[1].pk, low.pk)

    def test_trending_prefers_recent_when_raw_score_similar(self):
        now = timezone.now()
        old = make_post(self.channel, 1, views=100, forwards=0, when=now - timedelta(days=30))
        recent = make_post(self.channel, 2, views=100, forwards=0, when=now - timedelta(hours=1))
        ordered = list(apply_sort(Post.objects.all(), '-trending'))
        self.assertEqual(ordered[0].pk, recent.pk)
        self.assertEqual(ordered[1].pk, old.pk)

    def test_legacy_sort_still_works(self):
        a = make_post(self.channel, 1, views=10, when=timezone.now() - timedelta(days=1))
        b = make_post(self.channel, 2, views=20, when=timezone.now())
        ordered = list(apply_sort(Post.objects.all(), '-date'))
        self.assertEqual(ordered[0].pk, b.pk)
        self.assertEqual(ordered[1].pk, a.pk)
