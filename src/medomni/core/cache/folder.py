"""The `folder` cache backend, the default: each result in its own folder, kept until `gc` removes it.

    <path>/<dataset>/<step>/<key>/
        CACHE.json      the step, version, parameters, inputs and row counts: for `status` and `gc` only
        ...             the result's files

- A result is never changed. Running a step whose key is there already does nothing and returns it.
- A result is written into `<key>.tmp-<pid>/` and then renamed, so a crash leaves only a `.tmp-` folder, which `gc`
  removes. No links and no permission changes: it works on exFAT.
- No content hash: nothing checks what a result holds (R-111, R-155). Entries written before R-155 carry one; it is
  ignored.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Iterator

from . import CacheError, Result, check_rows, current_steps, key, refuse_links, size

META = "CACHE.json"
TMP = ".tmp-"


def _release() -> str:
    from medomni import __version__
    return __version__


class FolderCache:
    name = "folder"

    def __init__(self, path=None):
        if not path:
            raise CacheError("the folder cache needs a path (`cache: <absolute path>` in workspace.yaml)")
        root = Path(path)
        if not root.is_absolute():
            raise CacheError(f"cache path must be absolute: {root}")
        self.root = root

    @property
    def spec(self) -> dict:
        return {"backend": self.name, "path": str(self.root), "options": {}}

    def folder(self, dataset: str, step: str, k: str) -> Path:
        return self.root / dataset / step / k

    def run(self, dataset, step, version, params, inputs, make) -> tuple[Result, bool]:
        k = key(step, version, params, inputs)
        final = self.folder(dataset, step, k)
        if (final / META).is_file():
            return self.read(final), False
        final.parent.mkdir(parents=True, exist_ok=True)
        tmp = final.parent / f"{k}{TMP}{os.getpid()}"
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir()
        try:
            rows = check_rows(make(tmp))
            if (tmp / META).exists():
                raise CacheError(f"step {step} wrote its own {META}")
            refuse_links(tmp)
            meta = {"dataset": dataset, "step": step, "version": version, "key": k, "params": params,
                    "inputs": [{"name": n, "hash": h} for n, h in sorted(inputs)], "rows": rows, "release": _release()}
            (tmp / META).write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            try:
                os.rename(tmp, final)
            except OSError:
                if not (final / META).is_file():
                    raise
                shutil.rmtree(tmp)  # another process made the same result first
                return self.read(final), False
        except BaseException:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        return self.read(final), True

    @staticmethod
    def read(d: Path) -> Result:
        try:
            m = json.loads((d / META).read_text(encoding="utf-8"))
            return Result(path=d, dataset=m["dataset"], step=m["step"], version=str(m["version"]), key=m["key"],
                          params=m.get("params") or {}, inputs=tuple(i["name"] for i in m.get("inputs") or ()),
                          rows=m.get("rows") or {})
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise CacheError(f"{d / META}: unreadable ({type(e).__name__}: {e})") from None

    def folders(self) -> Iterator[Path]:
        """Every result folder and every `.tmp-` folder, sorted."""
        if not self.root.is_dir():
            return
        for d in sorted(self.root.glob("*/*/*")):
            if d.is_dir():
                yield d

    def results(self) -> Iterator[Result]:
        for d in self.folders():
            if TMP not in d.name:
                yield self.read(d)

    # ------------------------------------------------------------ optional features

    def has(self, dataset: str, step: str) -> bool:
        """Whether any result of this step is kept for this dataset."""
        return any((self.root / dataset / step).glob(f"*/{META}"))

    def status(self) -> dict:
        """{"where", "rows": [(dataset, step, results, bytes, in use)], "unfinished"}."""
        steps, rows, tmp = current_steps(), {}, 0
        for d in self.folders():
            if TMP in d.name:
                tmp += 1
                continue
            r = self.read(d)
            row = rows.setdefault((r.dataset, r.step), [0, 0, 0])
            row[0] += 1
            row[1] += size(d)
            row[2] += steps.get(r.step) == r.version
        return {"where": str(self.root), "rows": [(*k, *v) for k, v in sorted(rows.items())], "unfinished": tmp}

    def gc(self, dry_run: bool = False) -> list[tuple[str, str]]:
        """Remove results no current step version uses, and unfinished folders: [(folder, why)]."""
        steps, doomed = current_steps(), []
        for d in self.folders():
            if TMP in d.name:
                doomed.append((d, "unfinished"))
            else:
                r = self.read(d)
                if steps.get(r.step) != r.version:
                    doomed.append((d, "no current step uses it"))
        if not dry_run:
            for d, _ in doomed:
                shutil.rmtree(d)
        return [(d.relative_to(self.root).as_posix(), why) for d, why in doomed]
