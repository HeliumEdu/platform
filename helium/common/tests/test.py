__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.core.cache import cache
from django.test import TestCase


class CacheTestCase(TestCase):
    def tearDown(self):
        cache.clear()
