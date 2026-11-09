"""`medomni studio download-list <dataset>`: for a dataset downloaded in parts, the files its source population needs.

Needs the dataset's index tables on disk. The patients are chosen by the dataset's hash rule (R-32, R-41). A dataset with
a `download` hook (BDSP) lists each file's server key and its path in your copy; anything else is listed by each `tree`
entry's pattern, with the subject filled in.
"""
from __future__ import annotations

from pathlib import Path

from medomni.core import workspace

from ..tools import Preview, Result, ToolError


def source_rows(config, raw: Path) -> dict[str, dict]:
    """The source population's patients and each one's latest index row, by the dataset's hash rule."""
    from medomni.bench.build.pool import in_fraction
    from medomni.core.loading.options import options
    from medomni.core.loading.readers import csv_

    tables = {n: s for r in config.read if r.reader == "csv" for n, s in options(r).tables.items()}
    spec = tables.get(config.units.table)
    if spec is None:
        raise ToolError(f"units table {config.units.table} is not a csv table of the dataset")
    if not any(p.is_file() for p in csv_.files(spec, raw)):
        raise ToolError(f"index table {spec.file} is not on disk under {raw}; download the index first")
    latest: dict[str, dict] = {}
    for r in csv_.table_rows(spec, raw):
        s = r.get(config.units.column)
        if s and (s not in latest or (spec.time and r.get(spec.time, "") > latest[s].get(spec.time, ""))):
            latest[s] = r
    if config.source == "all":
        return latest
    return {s: r for s, r in latest.items() if in_fraction(config.source.salt, s, config.source.fraction)}


def download_hook(package: Path):
    """The package's `download` hook, or None."""
    from medomni.core.loading import hooks

    return hooks.module(package, "download", derives=False) if (package / "hooks" / "download.py").is_file() else None


def from_hooks(mod, config, rows: dict[str, dict]) -> list[tuple[str, str]]:
    """(server key, path in your copy) of the index tables and each patient's files."""
    from medomni.core.loading.options import options

    params = next(dict(options(r).params) for r in config.read if r.reader == "hook")
    out = list(mod.index_files())
    for s in sorted(rows):
        out += mod.night_files(params, rows[s])
    return out


def from_tree(config, subjects: list[str]) -> list[str]:
    from medomni.core.loading.options import options

    out: list[str] = []
    for r in config.read:
        if r.reader == "tree":
            for spec in options(r).files.values():
                out += [spec.pattern.format(subject=s, record="*") for s in subjects]
    return out


class DownloadList(Preview):
    name = "download-list"
    summary = "list the files a dataset's source population needs, for a dataset downloaded in parts"
    target = "dataset"

    def make(self, target, a, ctx) -> Result:
        from medomni.core.contracts import DatasetConfig, load
        from medomni.core.loading import find_package

        try:
            package = find_package(target)
        except FileNotFoundError as e:
            raise ToolError(str(e)) from None
        config = load(package / "dataset.yaml", DatasetConfig)
        raw = workspace.dataset_path(ctx.ws, target)
        mod = download_hook(package)
        try:
            rows = source_rows(config, raw)
        except ToolError as e:
            if mod is None:
                raise
            raise ToolError("\n".join([str(e), "Download these first (server key, then path in your copy):"]
                                       + ["  " + "  ".join(pair) for pair in mod.index_files()])) from None
        slug = f"{target}.txt"
        if mod is not None:
            pairs = from_hooks(mod, config, rows)
            text = "".join(f"{key}\t{local}\n" for key, local in pairs)
            return Result(f"{target}: {len(rows)} patients, {len(pairs)} files; server key and path in your copy, in {slug}", {slug: text})
        files = from_tree(config, sorted(rows))
        return Result(f"{target}: {len(rows)} patients, {len(files)} files; list in {slug}", {slug: "\n".join(files) + "\n"})
