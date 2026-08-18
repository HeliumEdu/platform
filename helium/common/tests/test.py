__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

from django.core.cache import cache
from django.test import TestCase


class CacheTestCase(TestCase):
    def tearDown(self):
        cache.clear()
