"""The `none` cache backend: nothing is kept between processes.

Each step runs into a temporary folder, which lives until the process ends (or `close()`). Within one process a step
with the same arguments runs once, so a build does not convert the same file twice. Rule 1 of the Cache page says a
build with this backend equals a build with any other.
"""
from __future__ import annotations

import atexit
import shutil
import tempfile
from pathlib import Path

from . import Result, check_rows, key, refuse_links


class NoCache:
    name = "none"

    def __init__(self, path=None):
        self._base = Path(path) if path else None  # where the temporary folders go; the system's temp folder if unset
        self._root: Path | None = None
        self._made: dict[str, Result] = {}

    @property
    def spec(self) -> dict:
        return {"backend": self.name, "path": str(self._base) if self._base else None, "options": {}}

    def _tmp(self) -> Path:
        if self._root is None or not self._root.is_dir():
            if self._base:
                self._base.mkdir(parents=True, exist_ok=True)
            self._root = Path(tempfile.mkdtemp(prefix="medomni-nocache-", dir=self._base))
            atexit.register(self.close)
        return self._root

    def run(self, dataset, step, version, params, inputs, make) -> tuple[Result, bool]:
        k = key(step, version, params, inputs)
        if k in self._made and self._made[k].path.is_dir():
            return self._made[k], False
        folder = self._tmp() / dataset / step / k
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True)
        try:
            rows = check_rows(make(folder))
            refuse_links(folder)
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        result = Result(path=folder, dataset=dataset, step=step, version=version, key=k, params=params,
                        inputs=tuple(n for n, _ in sorted(inputs)), rows=rows)
        self._made[k] = result
        return result, True

    def close(self) -> None:
        """Remove this process's temporary folders."""
        if self._root is not None:
            shutil.rmtree(self._root, ignore_errors=True)
            self._root = None
        self._made.clear()
