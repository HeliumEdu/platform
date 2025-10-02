__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import re

from django.core.cache.backends.locmem import LocMemCache


class LocMemKeysCache(LocMemCache):
    """
    Extends the generic in-memory cache to support the querying of keys, similar to how a Redis-based implementation
    might similar support this.
    """

    def keys(self, search):
        pattern = re.compile(self.make_key(search))

        keys = []
        for key, value in self._cache.items():
            if pattern.match(key):
                keys.append(key.removeprefix(':' + str(self.version)).removeprefix(':' + str(self.key_prefix)))

        return keys
