from django.core.cache import cache
from django.test import TestCase

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.2'


class CacheTestCase(TestCase):
    def tearDown(self):
        cache.clear()
