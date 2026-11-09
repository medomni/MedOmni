"""One JSONL line per call. Bench derives budget from it.

Never raises: a log that cannot be written must not turn a finished encode into
a failed request.
"""
# Changes on assurance/matrix (2026-09-17), for review by Perception:
#   M5  _append() was called but never defined, so every write failed silently and no call log was ever
#       written. Added (4 lines); behaviour of write() is otherwise unchanged.
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path


class CallLog:
    def __init__(self, path, log_paths=True):
        self.path = Path(path) if path else None
        # A request path can name a patient. false records a digest instead, so
        # repeated calls are still countable and the path itself is not kept.
        self.log_paths = log_paths
        self.failed = 0
        if self.path:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                print(f"call log disabled: {exc}", file=sys.stderr)
                self.path = None

    def _mask(self, path):
        if self.log_paths or path is None:
            return path
        return "sha256:" + hashlib.sha256(str(path).encode()).hexdigest()[:16]

    def _append(self, line):
        with open(self.path, "a") as f:
            f.write(line)

    async def write(self, **record):
        if not self.path:
            return
        record["path"] = self._mask(record.get("path"))
        record.setdefault("t", time.time())
        try:
            line = json.dumps(record, separators=(",", ":"), default=str) + "\n"
            await asyncio.to_thread(self._append, line)
        except Exception:
            self.failed += 1            # the call succeeded; the record did not
