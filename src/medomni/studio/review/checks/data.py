"""The audit's Data cells: a connected dataset's package, its copy and the event table. Each `D-*` id is one check."""
from __future__ import annotations

import io
import json
import re
from pathlib import Path

from medomni.core import plugins

from ...survey.dataset import declared_families
from ..matrix import FAIL, NONE, PASS, WARN

REQUIRED = ("dataset.yaml", "labels.yaml", "evidence.yaml", "codes.csv", "policy.yaml")
DIRECT_ID = re.compile(r"(^|_)(name|mrn|ssn|address|phone|email|zip)(_|$)", re.I)


def run(scope, sink) -> None:
    from medomni.studio import data as bench_data
    from medomni.core import workspace
    from medomni.core.contracts import ContractError, DatasetConfig, DatasetPolicy, load
    from medomni.core.loading import find_package

    repo = plugins.find_repo()
    for ds in scope.datasets:
        try:
            pkg = find_package(ds)
        except FileNotFoundError as e:
            sink.add("D-COMP.1", "M", ds, FAIL, str(e), "find_package")
            continue
        missing = [f for f in REQUIRED if not (pkg / f).is_file()]
        sink.add("D-COMP.1", "M", ds, FAIL if missing else PASS, f"missing: {missing}" if missing else "package files present", "package")
        config = load(pkg / "dataset.yaml", DatasetConfig)
        sink.add("D-COMP.2", "M", ds, PASS if config.description.version else FAIL, f"release {config.description.version}", "dataset.yaml")
        if (pkg / "policy.yaml").is_file():
            try:
                policy = load(pkg / "policy.yaml", DatasetPolicy)
                sink.add("D-COMP.2", "M", ds, PASS, f"license {policy.license.id}", "policy.yaml")
                sink.add("D-ISOL.2", "M", ds, PASS, "routes and publish rules declared", "policy.yaml")
            except ContractError as e:
                sink.add("D-COMP.2", "M", ds, FAIL, str(e), "policy.yaml")
        sink.add(*_event_table(scope.ws, ds))
        stream = io.StringIO()
        code = bench_data.check(ds, stream)  # the v1 builder's check of the package and the copy (R-125)
        problems = [ln.strip() for ln in stream.getvalue().splitlines() if ln.startswith("  ")]
        for p in (problems or ["`bench data check` failed without naming a problem"]) if code else ():
            sink.add("D-CONF.1", "M", ds, FAIL, p, "bench data check")
        if not code:
            sink.add("D-CONF.1", "M", ds, PASS, "`bench data check` passes", "bench data check")
        ok = config.source == "all" or (config.source.salt and config.source.fraction)
        sink.add("D-CONF.3", "M", ds, PASS if ok else FAIL, "source rule declared" if ok else "no source rule", "dataset.yaml")
        try:
            root = workspace.dataset_path(scope.ws, ds)
            inside = repo is not None and (root == repo or repo in root.parents)
            sink.add("D-ISOL.3", "M", ds, FAIL if inside else PASS, "data root inside the repository" if inside else "data root outside the repository", "workspace")
        except workspace.WorkspaceError as e:
            sink.add("D-ISOL.3", "M", ds, NONE, str(e), "workspace")
        families = declared_families(pkg)
        sink.add("D-COMP.3", "M", ds, PASS if families else WARN, f"{len(families)} families declared", "package")
    for pair in scope.pairs:
        _staged_columns(scope, sink, pair)


def _event_table(ws, ds: str) -> tuple:
    """D-COMP.3 from the cache backend's own status, when it has one; the cache only saves time, so no table is no fault."""
    from medomni.core import cache

    try:
        backend = cache.of(ws)
    except cache.CacheError as e:
        return "D-COMP.3", "M", ds, NONE, str(e), "cache"
    has = getattr(backend, "has", None)
    if has is None:
        return "D-COMP.3", "M", ds, NONE, f"the '{backend.name}' cache backend lists nothing", "cache"
    found = has(ds, "events")
    return ("D-COMP.3", "M", ds, PASS if found else NONE,
            "event table in the cache" if found else "no event table cached; run `medomni cache build`", "cache")


def _codes(pair: str) -> tuple[set, set]:
    """The pair's dataset codes (`codes.csv`): the codes, and (table, value) for each `<PREFIX>//<value>` code."""
    import csv

    from medomni.core.loading import find_package

    from ... import common

    path = find_package(common.load_pair(pair).template.dataset) / "codes.csv"
    if not path.is_file():
        return set(), set()
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return ({r["code"] for r in rows},
            {(r.get("source_table") or "", r["code"].split("//", 1)[1]) for r in rows if "//" in r["code"]})


def _coded(f: Path, column: str, codes: tuple[set, set]) -> bool:
    """True when every value of a staged table's column is one of the dataset's codes (VitalDB's `labs.name` holds
    lab test names such as `alb`, each a `LAB//alb` code): a coded field, not a direct identifier."""
    import csv

    with open(f, newline="", encoding="utf-8") as fh:
        values = {(r.get(column) or "").strip() for r in csv.DictReader(fh)}
    whole, by_table = codes
    return bool(values) and all(v in whole or (f.stem, v) in by_table for v in values)


def _staged_columns(scope, sink, pair: str) -> None:
    from ... import common

    codes = None
    for arm, _, atom, d in common.built_atoms(scope.ws, pair):
        cols, coded = set(), set()
        for f in (d / "data/tables").glob("*.csv"):
            with open(f, encoding="utf-8") as fh:
                heads = [h.strip() for h in fh.readline().split(",")]
            cols |= {f"{f.stem}.{h}" for h in heads}
            for h in heads:
                if DIRECT_ID.search(h):
                    codes = _codes(pair) if codes is None else codes
                    if _coded(f, h, codes):
                        coded.add(f"{f.stem}.{h}")
        demo = d / "data/demographics.json"
        if demo.exists():
            doc = json.loads(demo.read_text(encoding="utf-8"))
            cols |= {f"demographics.{k}" for k in (doc if isinstance(doc, dict) else {})}
        hit = sorted(c for c in cols - coded if DIRECT_ID.search(c.split(".", 1)[1]))
        sink.add("D-ISOL.1", "M", atom, FAIL if hit else PASS,
                 f"direct-identifier fields staged to the agent: {hit[:5]}" if hit else f"no direct-identifier field among {len(cols)} staged columns or keys"
                 + (f" ({', '.join(sorted(coded))} hold only dataset codes)" if coded else ""),
                 "atom tables")
