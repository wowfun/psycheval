"""Bounded, runtime-owned scoring projections with tracked file dependencies."""

from __future__ import annotations

import json
from collections import OrderedDict
from threading import Lock


class TaskInventoryCache:
    def __init__(self, *, max_bytes: int = 64 * 1024 * 1024, max_entries: int = 4096):
        self.max_bytes = max_bytes
        self.max_entries = max_entries
        self._entries = OrderedDict()
        self._size = 0
        self._lock = Lock()

    def get(self, key, *, load, read, signature):
        """Revalidate safe paths, including absent step overrides, on every hit."""

        def unchanged(dependencies):
            try:
                return all(
                    signature(path) == stamp for path, stamp in dependencies.items()
                )
            except (OSError, ValueError):
                return False

        with self._lock:
            entry = self._entries.pop(key, None)
            if entry is not None:
                dependencies, encoded = entry
                if unchanged(dependencies):
                    self._entries[key] = entry
                    # Callers receive independent mutable projections.
                    return json.loads(encoded)
                self._size -= len(encoded)

            dependencies, cacheable = {}, True

            def tracked_read(path):
                nonlocal cacheable
                try:
                    stamp = signature(path)
                    dependencies.setdefault(path, stamp)
                except (OSError, ValueError):
                    cacheable = False
                return read(path)

            value = load(tracked_read)
            if cacheable and unchanged(dependencies):
                encoded = json.dumps(value, ensure_ascii=False).encode("utf-8")
                if len(encoded) <= self.max_bytes and self.max_entries > 0:
                    self._entries[key] = (dependencies, encoded)
                    self._size += len(encoded)
                    while (
                        self._size > self.max_bytes
                        or len(self._entries) > self.max_entries
                    ):
                        _, (_, removed) = self._entries.popitem(last=False)
                        self._size -= len(removed)
            return value
