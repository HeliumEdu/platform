__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

from django.core.cache import cache
from django.test import TestCase


class CacheTestCase(TestCase):
    def tearDown(self):
        cache.clear()
