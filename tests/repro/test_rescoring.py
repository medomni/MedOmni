"""Check 5 (U3.4, R-88): v0.3's scorer, fed v0.2's saved submissions and gold, gives the baseline's numbers. No Harbor run.

T4: needs v0.2.1's checkout (MEDOMNI_V02) and the baseline run (MEDOMNI_BASELINE_SCORES). Prints counts only.
"""
from __future__ import annotations

import collections
import csv
import json
import os
from pathlib import Path

import pytest
import yaml

from medomni.bench.scoring import Refused, score_targets

from .paths import BASELINE_SCORES, V02 as V02_ENV, env, needs

pytestmark = [pytest.mark.baseline, needs(V02_ENV, BASELINE_SCORES)]
V02, BASE = env(V02_ENV), env(BASELINE_SCORES)
RUNS = V02 / "runs" if V02 else None


def declared(agent):
    f = V02 / "harness/harbor/agents" / f"{agent}.yaml"
    return (yaml.safe_load(open(f)).get("agents") or [{}])[0].get("model_name") if f.exists() else None


def parent_of(rows, task):
    batch = rows[0].get("batch")
    own = sorted({Path(x["atoms_root"]) for x in rows if x.get("atoms_root")})
    for root in own + [r for r in sorted((V02 / "data_task").glob("atomtasks*")) if r not in own]:
        for cand in (root / "_parents" / f"{task}__{batch}", root / "_parents" / task):
            if (cand / "parent.json").exists():
                return cand
    return None


def gold_of(pdir):
    metrics, gold = {}, collections.defaultdict(dict)
    for r in csv.DictReader(open(pdir / "gold.csv")):
        metrics[r["target"]] = r["metric_family"]
        gold[r["target"]][r["subject_id"]] = float(r["value"])
    return metrics, dict(gold)


def submission(path):
    return {r["target"]: float(r["prediction"]) for r in csv.DictReader(open(path))}


def resolve(p):
    q = Path(p)
    return q if q.is_absolute() else RUNS / q


def test_the_baselines_scores_come_back_from_predictions():
    if not BASE.is_dir():
        pytest.skip("needs the v0.2.1 baseline")
    latest = {}
    for line in open(RUNS / "ledger/results.jsonl"):
        r = json.loads(line)
        if r.get("run_id") and r.get("kind"):
            latest[r["run_id"]] = r
    cells = collections.defaultdict(list)
    for r in latest.values():
        if r["kind"] == "atom":
            cells[(r["experiment"], r["task"], r["agent"], r.get("variant"), r["rep"])].append(r)
    tally = collections.Counter()
    for row in (json.loads(x) for x in open(BASE / "scores.jsonl")):
        key = (row["experiment"], row["task"], row["agent"], row.get("variant"), row["rep"])
        rows = cells[key]
        want = declared(row["agent"]) or collections.Counter(x.get("model") for x in rows).most_common(1)[0][0]
        kept = [x for x in rows if x.get("model") == want]
        pdir = parent_of(kept, row["task"])
        cohort = set(json.load(open(pdir / "parent.json"))["cohort"])
        have = {}
        for x in kept:
            if x["subject_id"] in cohort and (x["subject_id"] not in have or (x.get("started_at") or "") > (have[x["subject_id"]].get("started_at") or "")):
                have[x["subject_id"]] = x
        metrics, gold = gold_of(pdir)
        failed = {s for s, x in have.items() if x.get("error")}
        preds = {s: ({} if s in failed else submission(resolve(x["submission_path"]))) for s, x in have.items()}
        try:
            got = score_targets(metrics, gold, preds, failed)
        except Refused:
            tally["refused"] += 1
            continue
        tally["rows"] += 1
        for t, v in row["targets"].items():
            tally["same" if got.values[t]["value"] == v["value"] else "differ"] += 1
    print(dict(tally))
    assert tally["rows"] == 105 and not tally["differ"] and not tally["refused"] and tally["same"] == 230


def test_v02s_runs_convert_to_records(tmp_path):
    if not (RUNS / "experiments/mid/jobs").is_dir():
        pytest.skip("needs v0.2.1's runs")
    from tests.repro.migrate.runs import import_all

    got = import_all(V02, tmp_path)
    print(dict(got))
    assert got["trials"] >= 5400 and got["submissions"] > 5000  # an unreadable submission is a failed atom, as in v0.2
