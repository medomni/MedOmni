"""Bounded LRU over Evidence, keyed by fingerprint.

The fingerprint covers the input's every file, the encoder, and the image that
actually ran, so it is the key the README asks for and it invalidates itself
when any of those change.

Bounded by bytes, not entries: one ECG Evidence carries a 1024-wide embedding,
so a few hundred entries is not a small number. In memory, and it dies with the
process.
"""
import json
from collections import OrderedDict


class Cache:
    """Touched only from the event loop, so it needs no lock."""

    def __init__(self, max_bytes=256 << 20):
        self.max_bytes = max_bytes
        self._entries = OrderedDict()
        self.bytes = 0
        self.hits = self.misses = 0

    def get(self, key):
        if not self.max_bytes or key not in self._entries:
            self.misses += 1
            return None
        self._entries.move_to_end(key)
        self.hits += 1
        return self._entries[key][0]

    def put(self, key, value):
        if not self.max_bytes:
            return
        size = len(json.dumps(value, default=str))
        if size > self.max_bytes:
            return                      # one entry that cannot share the budget
        if key in self._entries:
            self.bytes -= self._entries[key][1]
        self._entries[key] = (value, size)
        self._entries.move_to_end(key)
        self.bytes += size
        while self.bytes > self.max_bytes:
            _, (_, evicted) = self._entries.popitem(last=False)
            self.bytes -= evicted

    def stats(self):
        return {"entries": len(self._entries), "bytes": self.bytes,
                "max_bytes": self.max_bytes, "hits": self.hits, "misses": self.misses}
