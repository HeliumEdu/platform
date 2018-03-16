from django.test import TestCase

from django.core.cache import cache


class CacheTestCase(TestCase):
    def tearDown(self):
        cache.clear()
