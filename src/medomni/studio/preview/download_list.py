"""`medomni studio download-list <dataset>`: for a dataset downloaded in parts, the files its source population needs.

Needs the dataset's index tables on disk. The patients are chosen by the dataset's hash rule (R-32, R-41). A dataset with
a `download` hook lists each file's source, its path in your copy and how to fetch it; anything else is listed by each
`tree` entry's pattern, with the subject filled in.
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


def from_hooks(mod, config, raw: Path, rows: dict[str, dict]) -> list[tuple[str, str, str]]:
    """(source, path in your copy, how) of the index tables and of the source population's files."""
    from medomni.core.loading.options import options

    params = {options(r).hook: dict(options(r).params) for r in config.read if r.reader == "hook"}
    try:
        return list(mod.index_files()) + list(mod.files(raw, params, rows))
    except FileNotFoundError as e:
        raise ToolError(_first(f"{Path(e.filename).relative_to(raw) if e.filename else e} is not in your copy", mod)) from None


def _first(problem: str, mod) -> str:
    return "\n".join([problem, "Download these first (source, path in your copy, how):"]
                     + ["  " + "  ".join(entry) for entry in mod.index_files()])


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
            raise (e if mod is None else ToolError(_first(str(e), mod))) from None
        slug = f"{target}.txt"
        if mod is not None:
            entries = from_hooks(mod, config, raw, rows)
            text = "".join("\t".join(e) + "\n" for e in entries)
            return Result(f"{target}: {len(rows)} patients, {len(entries)} entries (source, path in your copy, how) in {slug}",
                          {slug: text})
        files = from_tree(config, sorted(rows))
        return Result(f"{target}: {len(rows)} patients, {len(files)} files; list in {slug}", {slug: "\n".join(files) + "\n"})
