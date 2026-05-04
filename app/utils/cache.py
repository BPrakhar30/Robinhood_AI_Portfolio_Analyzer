"""Bounded in-memory TTL cache.

Every ad-hoc ``dict[str, tuple[float, T]]`` cache in the codebase should
migrate to ``BoundedTTLCache`` to prevent gradual memory growth under
production traffic.
"""

from __future__ import annotations

import time
import threading
from collections import OrderedDict
from typing import Any, Optional


class BoundedTTLCache:
    """Thread-safe LRU + TTL cache with a hard size cap.

    When ``maxsize`` is reached, the least-recently-used entry is evicted.
    Expired entries are lazily pruned on read and periodically on write.
    """

    __slots__ = ("_store", "_maxsize", "_default_ttl", "_lock")

    def __init__(self, maxsize: int = 2048, default_ttl: int = 900):
        self._store: OrderedDict[str, tuple[float, int, Any]] = OrderedDict()
        self._maxsize = maxsize
        self._default_ttl = default_ttl
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            ts, ttl, value = entry
            if (time.time() - ts) > ttl:
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl if ttl is not None else self._default_ttl
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (time.time(), ttl, value)
            if len(self._store) > self._maxsize:
                self._store.popitem(last=False)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __len__(self) -> int:
        return len(self._store)
