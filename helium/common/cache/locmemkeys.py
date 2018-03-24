import re

from django.core.cache.backends.locmem import LocMemCache

__author__ = "Alex Laird"
__copyright__ = "Copyright 2018, Helium Edu"
__version__ = '1.4.3'


class LocMemKeysCache(LocMemCache):
    def keys(self, search):
        pattern = re.compile(self.make_key(search))

        keys = []
        with self._lock.reader():
            for key, value in self._cache.items():
                if pattern.match(key):
                    keys.append(key.lstrip(':' + str(self.version)).lstrip(':' + str(self.key_prefix)))

        return keys
