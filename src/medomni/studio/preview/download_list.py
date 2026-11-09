"""`medomni studio download-list <dataset>`: for a dataset downloaded in parts, the files its source population needs.

Needs the dataset's index tables on disk. The patients are chosen by the dataset's hash rule (R-32, R-41). A dataset
whose night-per-patient choice lives in a hook (BDSP's latest night) lists that file and its scoring companions;
anything else is listed by each `tree` entry's pattern, with the subject filled in.
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


def from_hooks(package: Path, config, rows: dict[str, dict]) -> list[str]:
    from medomni.core.loading import hooks
    from medomni.core.loading.options import options

    out: list[str] = []
    for r in config.read:
        if r.reader != "hook":
            continue
        o = options(r)
        mod = hooks.module(package, o.hook, derives=False)
        if not hasattr(mod, "h5_path"):
            continue
        for s in sorted(rows):
            rel = mod.h5_path(dict(o.params), rows[s])
            out += [rel, rel.replace(".h5", "_scores.csv"), rel.replace(".h5", "_events.csv")]
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
        rows = source_rows(config, raw)
        files = from_hooks(package, config, rows) or from_tree(config, sorted(rows))
        slug = f"{target}.txt"
        return Result(f"{target}: {len(rows)} patients, {len(files)} files; list in {slug}", {slug: "\n".join(files) + "\n"})
