from django.core.cache import cache
from django.test import TestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.37"


class CacheTestCase(TestCase):
    def tearDown(self):
        cache.clear()
