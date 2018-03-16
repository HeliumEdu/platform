from django.core.cache import cache
from django.test import TestCase


class CacheTestCase(TestCase):
    def tearDown(self):
        cache.clear()
