"""The audit's Run cells, read through the record contracts (`core/contracts/run.py`): the results file and each
run's `predictions.jsonl`. Part 5's scoring code is not imported; verifier replay stays unassessed until it runs."""
from __future__ import annotations

from pathlib import Path

from ... import common
from ..matrix import FAIL, NONE, PASS, WARN

GOLD_NAMES = ("gold.csv", "answers.csv", "content.json")


def run(scope, sink) -> None:
    from medomni.core.contracts import ContractError, PredictionRecord, load_lines

    runs, scores = scope.run_records
    if not runs and not scores:
        sink.add("R-COMP.1", "M", "*", NONE, "no records in the results file", "results")
        return
    sink.add("R-COMP.2", "M", "*", PASS, f"{len(runs)} run records and {len(scores)} score records", "results")
    root = Path(scope.ws.runs)
    for r in runs:
        rid = r.run_id
        preds = root / rid / "predictions.jsonl"
        have = preds.is_file()
        sink.add("R-COMP.1", "M", rid, PASS if have else FAIL, "predictions.jsonl present" if have else "no predictions.jsonl", "run folder")
        sink.add("R-COMP.1", "M", rid, PASS if r.model_served else WARN, "served model recorded" if r.model_served else "no served model recorded", "run record")
        recorded = r.api_cost is not None or r.error_kind is not None
        sink.add("R-COMP.2", "M", rid, PASS if recorded else WARN, "cost or error recorded" if recorded else "no cost and no error recorded", "run record")
        ok = _config_matches(scope.ws, r)
        if ok is None:
            sink.add("R-CONF.1", "M", rid, NONE, "the pair was not built here, or carries a v0.2 stand-in", "manifest")
        else:
            sink.add("R-CONF.1", "M", rid, PASS if ok else FAIL, "run config hash matches the build" if ok else "run config hash differs from the build manifest", "manifest")
        if have:
            try:
                n = len(load_lines(preds, PredictionRecord))
                sink.add("R-CONF.3", "M", rid, PASS, f"{n} prediction records valid", "prediction record")
            except ContractError as e:
                sink.add("R-CONF.3", "M", rid, FAIL, str(e), "prediction record")
        if r.agent is not None:
            leak = [p for p in r.agent.files_opened if any(g in p for g in GOLD_NAMES)]
            sink.add("R-ISOL.1", "M", rid, FAIL if leak else PASS, f"{len(leak)} gold-shaped files opened" if leak else f"{len(r.agent.files_opened)} files opened, none gold", "files opened")


def _config_matches(ws, r) -> bool | None:
    """The run's config hash against the build manifest's for its arm. None: nothing to compare."""
    if r.config_hash.startswith("v0.2:") or r.agent is None:
        return None
    m = common.manifest(ws, r.task)
    if m is None:
        return None
    key = f"{r.agent.arm}/{r.agent.arm_variant}" if r.agent.arm_variant else r.agent.arm
    return m["config_hash"].get(key) == r.config_hash
