"""`medomni studio survey <dataset>`: what a dataset has, from its event table (v0.2's manifest builder, in one tool).

The event table replaces v0.2's L0 scan, row cache and L1 patient manifests: codes, families, time spans and counts
per dataset. Demand and feasibility become one table of each cohort against the families the dataset supplies.
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import common
from ..tools import Result, Survey, ToolError

CRT, CMI = "clinical-record-table", "clinical-measurement-irregular"  # staged from tables by every dataset


def declared_families(package: Path) -> set[str]:
    """The families a dataset package says it can stage: its `tree` entries and hook `families`, plus the two table
    families. It replaces v0.2's hand-written `supply.yaml`."""
    from medomni.core.contracts import DatasetConfig, load
    from medomni.core.loading.options import options

    out = {CRT, CMI}
    for r in load(package / "dataset.yaml", DatasetConfig).read:
        o = options(r)
        if r.reader == "tree":
            for name, spec in o.files.items():
                out |= set(spec.families) if spec.format == "h5" else {name}
        elif r.reader == "hook":
            out |= set(o.params.get("families") or ())
    return out


def _cohorts(package: Path) -> list:
    from medomni.core.contracts import load
    from medomni.studio.build.contracts import Cohort, TaskTemplate
    from medomni.studio.build.contracts.recipe import Files

    rows = []
    for tdir in sorted((package / "tasks").glob("*/")):
        tpl = load(tdir / "template.yaml", TaskTemplate)
        for cp in sorted((tdir / "cohorts").glob("*.yaml")):
            if cp.name.endswith(".tests.yaml"):
                continue
            c = load(cp, Cohort)
            rows.append({"pair": f"{tpl.template_id}@{cp.stem}", "n": c.select.n, "by": list(c.select.by),
                         "targets": len(tpl.targets),
                         "families_required": sorted({f for q in c.require if isinstance(q, Files) for f in q.files})})
    return rows


class DatasetSurvey(Survey):
    name = "survey"
    summary = "report what a dataset has: codes, families, time spans, counts"
    target = "dataset"

    def make(self, target, a, ctx) -> Result:
        import pyarrow.compute as pc
        import pyarrow.parquet as pq

        from medomni.core import workspace
        from medomni.core import cache as cache_mod
        from medomni.core.contracts import DatasetConfig, load
        from medomni.core.loading import build, find_package

        try:
            package = find_package(target)
        except FileNotFoundError as e:
            raise ToolError(str(e)) from None
        config = load(package / "dataset.yaml", DatasetConfig)
        raw = workspace.dataset_path(ctx.ws, target)
        entry, _ = build(package, raw, cache_mod.of(ctx.ws), target)
        t = pq.read_table(entry.path / "events.parquet", columns=["subject_id", "time", "code"])
        subjects = len(pc.unique(t["subject_id"]))
        counts: dict[str, dict] = {}
        for code in pc.unique(t["code"]).to_pylist():
            sel = t.filter(pc.equal(t["code"], code))
            counts[code] = {"rows": sel.num_rows, "subjects": len(pc.unique(sel["subject_id"]))}
        times = [x for x in t["time"].to_pylist() if x is not None]
        families = {c[6:]: v for c, v in sorted(counts.items()) if c.startswith("FILE//")}
        cohorts = _cohorts(package)
        floor = max((c["n"] for c in cohorts), default=0)  # v0.2's cohort floor: enough subjects for the largest draw
        doc = {
            "dataset": target, "description": config.description.model_dump(), "subjects": subjects, "events": t.num_rows,
            "time_span": [min(times), max(times)] if times else None, "codes": dict(sorted(counts.items())),
            "families": families, "cohort_floor": floor, "cohorts": cohorts,
            "declared_families": sorted(declared_families(package)),
            "inputs": {"files": len(entry.inputs)}}
        rows = [[f, v["subjects"], v["rows"], "cohort-capable" if v["subjects"] >= floor else "evidence-only"]
                for f, v in families.items()]
        text = "\n".join([
            f"{target}: {subjects} subjects, {t.num_rows} events, {len(counts)} codes, {len(families)} file families",
            f"time span: {doc['time_span']}", "", common.table(["family", "subjects", "files", "role"], rows), "",
            common.table(["cohort", "n", "by", "families required"],
                         [[c["pair"], c["n"], ", ".join(c["by"]), ", ".join(c["families_required"])] for c in cohorts])])
        return Result(text, {f"{target}.json": json.dumps(doc, indent=1) + "\n", f"{target}.md": text + "\n"})
