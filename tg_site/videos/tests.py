from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from .models import Channel, Post
from .views import DEFAULT_SORT, apply_sort


def make_post(channel, telegram_id, *, views=0, forwards=0, replies=0, when=None, media_type='MessageMediaDocument', has_media=True):
    return Post.objects.create(
        channel=channel,
        telegram_id=telegram_id,
        date=when or timezone.now(),
        text='x',
        link='https://t.me/x/1',
        views=views,
        forwards=forwards,
        replies=replies,
        media_type=media_type,
        has_media=has_media,
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


class HomeDefaultFiltersTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.channel = Channel.objects.create(username='home_f', title='home_f')
        self.now = timezone.now()

    def test_implicit_date_range_excludes_post_older_than_week(self):
        make_post(self.channel, 1, when=self.now - timedelta(days=10))
        make_post(self.channel, 2, when=self.now - timedelta(days=1))
        response = self.client.get('/')
        self.assertEqual(response.context['total_count'], 1)

    def test_explicit_empty_date_params_means_all_time(self):
        make_post(self.channel, 1, when=self.now - timedelta(days=10))
        make_post(self.channel, 2, when=self.now - timedelta(days=1))
        response = self.client.get('/?date_from=&date_to=')
        self.assertEqual(response.context['total_count'], 2)

    def test_default_sort_in_context_is_trending(self):
        make_post(self.channel, 1)
        response = self.client.get('/')
        self.assertEqual(response.context['filters']['sort'], DEFAULT_SORT)

    def test_implicit_default_has_from_only_no_date_to(self):
        make_post(self.channel, 1)
        response = self.client.get('/')
        self.assertTrue(response.context['filters']['date_from'])
        self.assertEqual(response.context['filters']['date_to'], '')
        self.assertEqual(response.context['filters']['default_date_to'], '')

    def test_home_viral_sort_orders_by_ratio(self):
        low_ratio = make_post(self.channel, 1, views=10000, forwards=5, when=self.now - timedelta(days=1))
        high_ratio = make_post(self.channel, 2, views=100, forwards=40, when=self.now - timedelta(days=1))
        response = self.client.get('/?sort=-viral')
        ordered_ids = [p.id for p in response.context['page_obj']]
        self.assertEqual(ordered_ids[0], high_ratio.id)
        self.assertIn(low_ratio.id, ordered_ids)
