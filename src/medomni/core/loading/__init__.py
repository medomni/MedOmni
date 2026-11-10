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


def verify(config, readers, raw_root: Path, package: Path | None = None) -> None:
    from . import hooks
    from .readers import csv_, tree

    missing = []
    for kind, o in readers:
        if kind == "csv":
            for s in o.tables.values():
                if not csv_.files(s, raw_root) or not all(p.is_file() for p in csv_.files(s, raw_root)):
                    missing.append(s.file)
        elif kind == "hook" and package is not None:
            missing += [f for f in hooks.inputs(package, o.hook, raw_root, o.params) if not (raw_root / f).exists()]
    if missing:
        raise LoadError(f"verify: missing {len(missing)} listed file(s): {', '.join(sorted(missing))}")
    unknown = sorted(set(config.verify) - set(VERIFY))
    if unknown:
        raise LoadError(f"verify: unknown check {', '.join(unknown)} (known: {', '.join(VERIFY)})")
    if "version" in config.verify:
        found = copy_version(raw_root, config.verify["version"])
        if found != config.description.version:
            raise LoadError(f"verify: the copy is version {found!r}; the package describes {config.description.version!r}")
    if "manifests" in config.verify:
        bad = manifest_problems(raw_root, str(config.verify["manifests"]))
        if bad:
            raise LoadError(f"verify: {len(bad)} file(s) a manifest lists are missing, such as {bad[0]}")


VERIFY = ("unit_files", "manifests", "version")
NO_FILE = ("", "None", "Not reported", None)  # what a manifest writes where it lists no file


def copy_version(raw_root: Path, rule: dict) -> str | None:
    """The copy's version by the package's `verify.version` rule: `{file, key}` reads a JSON field; `{file, contains,
    version}` is that version when the file holds the text. None when the file is missing or says nothing."""
    p = raw_root / rule["file"]
    if not p.is_file():
        return None
    if "key" in rule:
        doc = json.loads(p.read_text(encoding="utf-8"))
        return str(doc.get(rule["key"])) if isinstance(doc, dict) and rule["key"] in doc else None
    return str(rule["version"]) if rule["contains"] in p.read_text(encoding="utf-8", errors="replace") else None


def missing_columns(readers, raw_root: Path) -> list[str]:
    """`<file>: <column>` for every column a csv table's options name that its first file lacks."""
    from .readers import csv_

    out = []
    for kind, o in readers:
        if kind != "csv":
            continue
        for name, spec in o.tables.items():
            paths = csv_.files(spec, raw_root)
            if not paths or not paths[0].is_file():
                continue
            have = set(csv_.columns(paths[0]))
            out += [f"{spec.file}: {c}" for c in spec.column_names() if c not in have]
    return out


def manifest_problems(raw_root: Path, pattern: str) -> list[str]:
    """Paths a manifest's `*filepath` or `*file_path` columns name that do not exist (manifests: tab-separated, paths
    relative to the data root or to the manifest's folder; `None` and `Not reported` mean no file)."""
    import csv as csvmod

    bad = []
    for m in sorted(raw_root.glob(pattern)):
        with open(m, newline="", encoding="utf-8") as f:
            for row in csvmod.DictReader(f, delimiter="\t"):
                for col, val in row.items():
                    if col and col.endswith(("filepath", "file_path")) and val not in NO_FILE:
                        rel = val.lstrip("/")
                        if not ((raw_root / rel).exists() or (m.parent / rel).exists()):
                            bad.append(f"{m.relative_to(raw_root).as_posix()}: {col}")
    return bad


def subject_maps(readers, raw_root: Path) -> dict:
    """For each tree entry with `subject_from`: the key column's value -> the table's subject id."""
    from .readers import csv_

    tables = {n: s for kind, o in readers if kind == "csv" for n, s in o.tables.items()}
    out = {}
    for kind, o in readers:
        if kind != "tree":
            continue
        for entry, spec in o.files.items():
            if spec.subject_from:
                t = tables.get(spec.subject_from.table)
                if t is None:
                    raise LoadError(f"read: files.{entry}: subject_from names {spec.subject_from.table}, "
                                    f"not a csv table")
                out[entry] = {r.get(spec.subject_from.key, ""): r.get(t.subject, "")
                              for r in csv_.table_rows(t, raw_root)}
    return out


def load(package: str | Path, raw_root: str | Path, out: str | Path, *, tables: set[str] | None = None,
         families: set[str] | None = None, codes: tuple[str, ...] | None = None) -> LoadResult:
    """Load `raw_root` by the dataset package at `package` and write the event table into `out`."""
    from medomni.core import families as registry
    from medomni.core.contracts import DatasetConfig, EventTable, load as load_contract, load_data

    from . import hooks
    from .readers import csv_, tree
    from .rules import apply

    package, raw_root, out = Path(package), Path(raw_root), Path(out)
    config = load_contract(package / "dataset.yaml", DatasetConfig)
    readers = [(r.reader, options(r)) for r in config.read]
    known = _codes(package)

    verify(config, readers, raw_root, package)
    stats: dict = {}
    rows: list[dict] = []
    maps = subject_maps(readers, raw_root) if tables is None else {}
    for kind, o in readers:
        if kind == "csv":
            rows += csv_.read(o, raw_root, tables=tables, stats=stats)
        elif kind == "tree" and tables is None:
            rows += tree.read(o, raw_root, families=families, stats=stats, subject_maps=maps)
    for kind, o in readers:
        if kind == "hook" and tables is None:
            new = hooks.derive(package, o.hook, rows, raw_root, o.params)
            stats[f"hook:{o.hook}"] = len(new)
            rows += new
    if codes is not None:
        keep = [re.compile(c) for c in codes]
        rows = [r for r in rows if any(k.search(r["code"]) for k in keep)]
    unit = config.units
    if "unit_files" in config.verify:
        pattern = str(config.verify["unit_files"])  # the file itself: a unit may have no row naming a family
        lacking = sorted(u for u in {r["subject_id"] for r in rows} if not (raw_root / pattern.format(unit=u)).is_file())
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


def dataset_packages() -> list[Path]:
    """Every dataset package, where the projects' `datasets` content kind says (R-145): the repository first, then the
    plug-in folders, then Core's dummy packages."""
    from medomni.core import plugins
    from medomni.core.testing import DATASETS

    roots, _ = plugins.roots(plugins.find_repo())
    out = []
    for kind in (k for k in plugins.content_kinds()[0] if k.name == "datasets"):
        for _, root in roots:
            for marker in sorted(root.glob(kind.marker)):
                d = marker
                for _ in range(kind.depth):
                    d = d.parent
                out.append(d)
    return out + sorted(p.parent for p in DATASETS.glob("*/dataset.yaml"))


def find_package(name: str | Path) -> Path:
    """A dataset package: a folder holding dataset.yaml, or a name looked up where a project's `datasets` content kind
    says (`medomni.content`, R-145), in the repository and then the plug-in folders, then Core's dummy packages."""
    p = Path(name)
    if (p / "dataset.yaml").is_file():
        return p
    for d in dataset_packages():
        if d.name == str(name):
            return d
    raise FileNotFoundError(f"no dataset package '{name}' (give a folder holding dataset.yaml, or a dataset name)")


def inputs(package: Path, raw_root: Path) -> list[tuple[str, str]]:
    """(name, hash) of everything the load reads, the cache key's inputs: the package's config and codes and every
    table file by sha256; every family file by its quick identity, since its bytes are not read by the load."""
    from medomni.core import hashing
    from medomni.core.contracts import DatasetConfig, load as load_contract

    from . import hooks
    from .readers import csv_, tree
    from .readers.headers import file_hash

    package, raw_root = Path(package), Path(raw_root)
    config = load_contract(package / "dataset.yaml", DatasetConfig)
    out = [(f"package/{f}", hashing.sha256_file(package / f)) for f in ("dataset.yaml", "codes.csv")]
    for r in config.read:
        o = options(r)
        if r.reader == "csv":
            out += [(p.relative_to(raw_root).as_posix(), hashing.sha256_file(p)) for s in o.tables.values()
                    for p in csv_.files(s, raw_root) if p.is_file()]
        elif r.reader == "tree":
            for spec in o.files.values():
                out += [(rel, file_hash(f)) for f, rel, _ in tree.matches(spec, raw_root)]
        elif r.reader == "hook":
            out.append((f"package/hooks/{o.hook}.py", hashing.sha256_file(package / "hooks" / f"{o.hook}.py")))
            for rel in hooks.inputs(package, o.hook, raw_root, o.params):
                p = raw_root / rel
                if p.exists():
                    table = p.suffix in (".csv", ".tsv", ".parquet", ".gz")
                    out.append((rel, hashing.dir_hash(p) if p.is_dir() else
                                hashing.sha256_file(p) if table else file_hash(p)))
    return sorted(set(out))


def build(package: str | Path, raw_root: str | Path, cache, dataset: str | None = None):
    """Load a dataset into the cache as the `events` entry. Returns (entry, created)."""
    from medomni.core.cache import CORE_STEPS

    package = Path(package)
    return cache.create(dataset or package.name, STEP, CORE_STEPS[STEP], {}, inputs(package, Path(raw_root)),
                        lambda d: {"events": load(package, raw_root, d).rows})
