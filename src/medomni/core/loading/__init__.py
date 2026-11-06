"""Loading a dataset into an event table (part 6; R-29, R-31, R-51).

    from medomni.core.loading import load
    result = load(package_dir, raw_root, out_dir)   # writes out_dir/events.parquet and out_dir/event-table.json

Five steps, each stopping with a `LoadError` that names what failed:

| Step | Does |
|---|---|
| verify | every table file the config lists exists; `verify.unit_files` (one file per unit) holds |
| read | each format reader turns its files into rows (`csv`, `tree`); a `tables` or `families` filter reads less |
| rules | the config's timing and visit rules (`rules.py`) |
| write | the event table (Parquet), sorted, with the event columns of R-29 and the file columns |
| check | every code is known (`codes.csv`, or a shared code); every `FILE` row names a known family; times parse |

Two loads of the same raw folder give the same Parquet bytes.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .options import options
from .readers import LoadError

# Shared codes (R-28): every dataset may emit these without listing them in codes.csv
SHARED = re.compile(r"^(ADMISSION|DISCHARGE|DEATH|ICU_ADMISSION|RECORDING//START|RECORDING//END|DIAGNOSIS//ICD//.+)$")
EVENTS, DESCRIPTION = "events.parquet", "event-table.json"


@dataclass(frozen=True)
class LoadResult:
    path: Path  # events.parquet
    rows: int
    subjects: int
    rows_read: dict  # rows (tables) or files (tree entries) read, by name


def _codes(package: Path) -> set[str]:
    with open(package / "codes.csv", newline="", encoding="utf-8") as f:
        return {r["code"] for r in csv.DictReader(f)}


def _time(raw: str | None, kind: str, where: str) -> str | None:
    if raw is None or raw == "":
        return None
    s = str(raw).strip().replace(" ", "T")
    try:
        if kind == "visit-dates":
            return date.fromisoformat(s[:10]).isoformat()
        if kind == "seconds-from-start":
            return str(float(s))
        return datetime.fromisoformat(s).replace(tzinfo=None).isoformat(timespec="seconds")
    except ValueError:
        raise LoadError(f"check: {where}: time '{raw}' is not a {kind} time") from None


def verify(config, readers, raw_root: Path) -> None:
    missing = []
    for kind, o in readers:
        if kind == "csv":
            missing += [s.file for s in o.tables.values() if not (raw_root / s.file).is_file()]
    if missing:
        raise LoadError(f"verify: missing {len(missing)} listed file(s): {', '.join(sorted(missing))}")
    unknown = sorted(set(config.verify) - {"unit_files"})
    if unknown:
        raise LoadError(f"verify: unknown check {', '.join(unknown)} (known: unit_files)")


def load(package: str | Path, raw_root: str | Path, out: str | Path, *, tables: set[str] | None = None,
         families: set[str] | None = None, codes: tuple[str, ...] | None = None) -> LoadResult:
    """Load `raw_root` by the dataset package at `package` and write the event table into `out`."""
    from medomni.core import families as registry
    from medomni.core.contracts import DatasetConfig, EventTable, load as load_contract, load_data

    from .readers import csv_, tree
    from .rules import apply

    package, raw_root, out = Path(package), Path(raw_root), Path(out)
    config = load_contract(package / "dataset.yaml", DatasetConfig)
    readers = [(r.reader, options(r)) for r in config.read]
    known = _codes(package)

    verify(config, readers, raw_root)
    stats: dict = {}
    rows: list[dict] = []
    for kind, o in readers:
        if kind == "csv":
            rows += csv_.read(o, raw_root, tables=tables, stats=stats)
        elif kind == "tree" and tables is None:
            rows += tree.read(o, raw_root, families=families, stats=stats)
    if codes is not None:
        keep = [re.compile(c) for c in codes]
        rows = [r for r in rows if any(k.search(r["code"]) for k in keep)]
    unit = config.units
    if "unit_files" in config.verify:
        have = {r["subject_id"] for r in rows if r["code"].startswith("FILE//")}
        lacking = sorted({r["subject_id"] for r in rows} - have)
        if lacking:
            raise LoadError(f"verify: {len(lacking)} units have no file (unit_files), such as {lacking[0]}")

    rows = apply(dict(config.rules), rows)
    kind = config.description.time
    fams = set(registry.load_registry())
    for r in rows:
        where = r.pop("_table") or r["path"]
        r["time"] = _time(r["time"], kind, f"{where}, subject {r['subject_id']}")
        code = r["code"]
        if code.startswith("FILE//"):
            if code[6:] not in fams:
                raise LoadError(f"check: {where}: unknown family {code[6:]}")
        elif code not in known and not SHARED.match(code):
            raise LoadError(f"check: {where}: code {code} is not in codes.csv and is not a shared code")
    rows.sort(key=lambda r: (r["subject_id"], r["time"] is not None, r["time"] or "", r["code"],
                             "" if r["numeric_value"] is None else repr(r["numeric_value"]), r["text_value"] or "",
                             r["path"] or ""))
    del unit

    import pyarrow as pa
    import pyarrow.parquet as pq

    schema = pa.schema([("subject_id", pa.string()), ("time", pa.string()), ("code", pa.string()),
                        ("numeric_value", pa.float64()), ("text_value", pa.string()), ("visit_id", pa.string()),
                        ("path", pa.string()), ("sha256", pa.string()), ("native_id", pa.string())])
    table = pa.Table.from_pylist(rows, schema=schema)
    out.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out / EVENTS, compression="zstd", use_dictionary=False, write_statistics=False)
    subjects = len({r["subject_id"] for r in rows})
    desc = load_data({"dataset": package.name, "description": config.description.model_dump(),
                      "rows": len(rows), "subjects": subjects}, EventTable, str(out / DESCRIPTION))
    (out / DESCRIPTION).write_text(json.dumps(desc.model_dump(mode="json"), indent=1) + "\n", encoding="utf-8")
    return LoadResult(out / EVENTS, len(rows), subjects, stats)


STEP = "events"  # the loading step's name in the cache; its version is cache.CORE_STEPS["events"]


def find_package(name: str | Path) -> Path:
    """A dataset package: a folder holding dataset.yaml, or a name looked up in the repository's `bench/datasets/`,
    the plug-in folders, then Core's dummy packages."""
    from medomni.core import plugins
    from medomni.core.testing import DATASETS

    p = Path(name)
    if (p / "dataset.yaml").is_file():
        return p
    roots, _ = plugins.roots(plugins.find_repo())
    for d in [root / "bench" / "datasets" / str(name) for _, root in roots] + [DATASETS / str(name)]:
        if (d / "dataset.yaml").is_file():
            return d
    raise FileNotFoundError(f"no dataset package '{name}' (give a folder holding dataset.yaml, or a dataset name)")


def inputs(package: Path, raw_root: Path) -> list[tuple[str, str]]:
    """(name, sha256) of everything the load reads: the package's config and codes, every table file and every
    family file the readers find. These are the cache key's inputs."""
    from medomni.core import hashing
    from medomni.core.contracts import DatasetConfig, load as load_contract

    from .readers import tree
    from .readers.headers import file_hash

    package, raw_root = Path(package), Path(raw_root)
    config = load_contract(package / "dataset.yaml", DatasetConfig)
    out = [(f"package/{f}", hashing.sha256_file(package / f)) for f in ("dataset.yaml", "codes.csv")]
    for r in config.read:
        o = options(r)
        if r.reader == "csv":
            out += [(s.file, hashing.sha256_file(raw_root / s.file)) for s in o.tables.values()
                    if (raw_root / s.file).is_file()]
        elif r.reader == "tree":
            for spec in o.files.values():
                rx = tree._regex(spec.pattern)
                for f in sorted(raw_root.glob(re.sub(r"\{(subject|record)\}", "*", spec.pattern))):
                    rel = f.relative_to(raw_root).as_posix()
                    if f.is_file() and rx.match(rel):
                        out.append((rel, file_hash(f)))
    return sorted(set(out))


def build(package: str | Path, raw_root: str | Path, cache, dataset: str | None = None):
    """Load a dataset into the cache as the `events` entry. Returns (entry, created)."""
    from medomni.core.cache import CORE_STEPS

    package = Path(package)
    return cache.create(dataset or package.name, STEP, CORE_STEPS[STEP], {}, inputs(package, Path(raw_root)),
                        lambda d: {"events": load(package, raw_root, d).rows})
