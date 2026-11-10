"""v0.2's runs as records (R-88, R-90): one record per trial, from each trial's saved files. No Harbor run.

Each v0.2 tree that was run becomes a set: `v0.2-ladder`, `v0.2-forced`, `v0.2-mid`. Records are version 0, with a `v0.2:`
config hash over the v0.2 template's own file at the release commit (R-90, as amended by R-111).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from collections import Counter
from pathlib import Path

from medomni import __version__
from medomni.core.contracts import IntelligenceRef, PredictionRecord, RunRecord, load_data
from tests.repro.migrate.templates import NAME_MAP

from medomni.bench.runs.harbor import classify_error, served_model

RELEASE_COMMIT = "aa45b68"
ARMS = {"enc": "encoders", "noenc": "no-perception", "enc-forced": "encoders-required", "ladder": "modality-ladder"}
SETS = {"ladder-mid-r": "v0.2-ladder", "smoke-forced": "v0.2-forced", "mid": "v0.2-mid"}


def set_of(experiment: str) -> str | None:
    for prefix, name in SETS.items():
        if experiment == prefix or (prefix != "mid" and experiment.startswith(prefix)):
            return name
    return None


def _config_hash(v02: Path, old_id: str, memo: dict) -> str:
    if old_id not in memo:
        spec = subprocess.run(["git", "-C", str(v02), "show", f"{RELEASE_COMMIT}:data_task/taskbuilder/specs/{old_id}.yaml"],
                              capture_output=True, check=True).stdout
        memo[old_id] = "v0.2:" + hashlib.sha256(spec).hexdigest()
    return memo[old_id]


def _trials(job: Path):
    for t in sorted(p for p in job.iterdir() if p.is_dir() and (p / "result.json").is_file()):
        yield t, json.loads((t / "result.json").read_text(encoding="utf-8"))


def import_job(v02: Path, job: Path, out: Path, memo: dict) -> Counter:
    """One job folder into `<out>/<set>/<job>/{runs,predictions}.jsonl`. Returns counts."""
    exp, agent, variant, rep, _ = job.name.split("--")
    task_set = set_of(exp)
    who = {"kind": "agent", "name": agent}
    d = out / task_set / job.name
    d.mkdir(parents=True, exist_ok=True)
    tally = Counter()
    with open(d / "runs.jsonl", "w", encoding="utf-8") as runs, open(d / "predictions.jsonl", "w", encoding="utf-8") as preds:
        for trial, result in _trials(job):
            task = result["task_id"]["path"] if isinstance(result.get("task_id"), dict) else str(result.get("task_id"))
            old, subject, batch = Path(task).name.split("__")
            cohort = "ladder" if batch.startswith("r") and batch[1:].isdigit() else batch
            rung = batch if cohort == "ladder" else None
            atom = f"{NAME_MAP.get(old, old)}__{subject}__{cohort}"
            run_id = f"{job.name}/{atom}{f'.{rung}' if rung else ''}"
            error = result.get("exception_info")
            sub = trial / "verifier/submission.csv"
            rows = None
            if sub.is_file():
                try:
                    rows = [(r["target"], float(r["prediction"])) for r in csv.DictReader(open(sub, newline="", encoding="utf-8"))]
                    if not all(math.isfinite(v) for _, v in rows):
                        raise ValueError("not a finite number")
                    tally["submissions"] += 1
                except (KeyError, ValueError, TypeError):
                    rows = None
                    tally["unreadable submissions"] += 1  # v0.2's scorer treats the whole submission as failed
            kind = classify_error(error) or ("agent" if rows is None else None)
            doc = {"kind": "run", "run_id": run_id, "release": __version__, "task_set": f"medomni-bench/{task_set}",
                   "task": f"{NAME_MAP.get(old, old)}@{cohort}", "task_version": "0.0", "config_hash": _config_hash(v02, old, memo),
                   "intelligence": who, "model_served": served_model(trial), "error_kind": kind,
                   "agent": {"arm": ARMS[variant], "arm_variant": rung}}
            runs.write(json.dumps(load_data(doc, RunRecord, run_id).model_dump(mode="json")) + "\n")
            tally["trials"] += 1
            for target, value in rows or ():
                rec = load_data({"run_id": run_id, "atom": atom, "target": target, "value": value, "intelligence": who}, PredictionRecord, run_id)
                preds.write(json.dumps(rec.model_dump(mode="json")) + "\n")
                tally["predictions"] += 1
    return tally


def import_all(v02: Path, out: Path) -> Counter:
    total, memo = Counter(), {}
    for exp_dir in sorted((v02 / "runs/experiments").iterdir()):
        if set_of(exp_dir.name) is None or not (exp_dir / "jobs").is_dir():
            continue
        for job in sorted(p for p in (exp_dir / "jobs").iterdir() if p.is_dir() and len(p.name.split("--")) == 5):
            total.update(import_job(v02, job, out, memo))
            total["jobs"] += 1
    return total
