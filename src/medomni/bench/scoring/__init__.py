"""The one scorer (R-118): prediction records and gold in, score rows out. Nothing else turns a run into a number.

Rules from v0.2's scorer, kept:

- every patient of the cohort is present, or the cell is refused, never partly scored;
- an agent failure is a real result, imputed at chance on probability targets; an infrastructure failure refuses the cell;
- a target with no prediction from a patient refuses the cell;
- a target marked `too_few` by Build has no value;
- a refusal is written as a row with no value, so a stale number can never stand as the latest for that row;
- on an arm with the perception service, each row carries the cell's encoder use (`encoder_use.py`).
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from medomni import __version__
from medomni.bench.metrics import auc, mae, qwk
from medomni.bench.scoring import encoder_use

METRICS = {"auc": auc, "qwk": qwk, "mae": mae}
FAILED = "agent"  # RunRecord.error_kind of a failure that is a real result
CHANCE = 0.5


class Refused(RuntimeError):
    """The cell can't be scored; the message says why."""


@dataclass(frozen=True)
class Outcome:
    values: dict[str, dict]  # target -> {metric, value, n}
    flags: list[str]


def constant(preds: list[float]) -> bool:
    return len(set(preds)) <= 1 and len(preds) > 1


def score_targets(metrics: dict[str, str], gold: dict[str, dict[str, float]], preds: dict[str, dict[str, float]],
                  failed: set[str] = frozenset()) -> Outcome:
    """Score each target. `gold`: target -> subject -> answer; `preds`: subject -> target -> prediction."""
    values, flags = {}, []
    for target, answers in gold.items():
        metric = metrics[target]
        pairs, absent, incomplete = [], [], 0
        for subject, answer in answers.items():
            p = preds.get(subject, {})
            if target in p:
                pairs.append((answer, p[target]))
            elif subject in failed:
                if metric == "auc":
                    pairs.append((answer, CHANCE))
                else:
                    incomplete += 1  # nothing to impute for a value or a class
            else:
                absent.append(subject)
        if absent:
            raise Refused(f"target {target} missing from {len(absent)} submissions")
        value = METRICS[metric](pairs)
        values[target] = {"metric": metric, "value": value, "n": len(pairs)}
        if incomplete:
            flags.append(f"{target}: incomplete ({incomplete} failed atoms not imputable)")
        if value is None:
            flags.append(f"{target}: unscorable (one-class or degenerate)")
        if constant([q for _, q in pairs]):
            flags.append(f"{target}: constant predictions")
    return Outcome(values, flags)


# ---- v0.3 runs
def read_gold(content: Path) -> tuple[dict, dict, dict]:
    """(metrics, gold, subject of atom) from a pair's content folder; a `too_few` target's answers are left out."""
    meta = json.loads((content / "content.json").read_text(encoding="utf-8"))
    too_few = {t["name"] for t in meta["targets"] if t.get("too_few")}
    metrics, gold = {}, defaultdict(dict)
    with open(content / "answers.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["target"] in too_few or r["value"] == "":
                continue
            metrics[r["target"]] = r["metric"]
            gold[r["target"]][r["subject_id"]] = float(r["value"])
    return metrics, dict(gold), {a["atom"]: a["subject"] for a in meta["atoms"]}


def score_run(job: Path, content_root: Path, task_set_hash: str, results: Path) -> list[dict]:
    """One job folder's runs into score rows, appended to the workspace's results file."""
    from medomni.core.contracts import PredictionRecord, RunRecord, load_lines

    runs = load_lines(job / "runs.jsonl", RunRecord)
    preds = load_lines(job / "predictions.jsonl", PredictionRecord)
    by_pair: dict[str, list] = defaultdict(list)
    for r in runs:
        by_pair[r.task].append(r)
    values = defaultdict(lambda: defaultdict(dict))
    for p in preds:
        values[p.run_id][p.target] = float(p.value)
    use = None  # run_id -> graded encoder calls; only a job whose arm has the perception service writes the file
    if (job / "encoder_use.jsonl").is_file():
        use = {}
        for line in open(job / "encoder_use.jsonl", encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                use[r["run_id"]] = r["calls"]
    rows = []
    for pair, group in sorted(by_pair.items()):
        rows += _score_pair(pair, group, values, content_root / pair, task_set_hash, use)
    with open(results, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return rows


def _score_pair(pair: str, runs: list, values: dict, content: Path, task_set_hash: str, use: dict | None = None) -> list[dict]:
    from medomni.core.contracts import ScoreRecord, load_data

    metrics, gold, subject_of = read_gold(content)
    meta = json.loads((content / "content.json").read_text(encoding="utf-8"))
    first = runs[0]
    job = first.run_id.split("/", 1)[0]
    used = {} if use is None else encoder_use.summary({r.run_id: use.get(r.run_id, []) for r in runs}, len(subject_of))

    def row(target: str, metric: str, value, flags, n_failed: int = 0) -> dict:
        doc = {"kind": "score", "run_id": f"{job}/{pair}/{target}", "release": __version__,
               "task_set": first.task_set, "task_set_hash": task_set_hash, "target": target,
               "task_version": first.task_version, "config_hash": first.config_hash, "arm": first.agent.arm if first.agent else None,
               "arm_variant": first.agent.arm_variant if first.agent else None, "n_atoms": len(subject_of), "n_failed": n_failed,
               "intelligence": first.intelligence.model_dump(mode="json"), "metric": metric, "value": value, "flags": list(flags),
               "encoder_use": used}
        return load_data(doc, ScoreRecord, doc["run_id"]).model_dump(mode="json", exclude_none=True, exclude_defaults=False)

    def marked():
        return [row(t["name"], t["metric"], None, [f"{t['name']}: too few in a class"])
                for t in meta["targets"] if t.get("too_few")]

    try:
        if len({r.config_hash for r in runs}) > 1:
            raise Refused("runs span several config hashes")
        have, failed = {}, set()
        for r in runs:
            have[r.run_id.split("/", 1)[1]] = r
        missing = set(subject_of) - set(have)
        if missing:
            raise Refused(f"incomplete: {len(missing)} atoms have no run")
        for atom, r in have.items():
            if r.error_kind:
                if r.error_kind != FAILED:
                    raise Refused(f"infrastructure failure on {atom}: resume the job")
                failed.add(subject_of[atom])
        preds = {subject_of[a]: dict(values.get(have[a].run_id, {})) for a in subject_of}
        for atom, s in subject_of.items():
            if s not in failed and not preds[s]:
                raise Refused(f"no readable submission for {atom}")
        outcome = score_targets(metrics, gold, preds, failed)
    except Refused as e:
        return [row(t, m, None, [f"refused: {e}"]) for t, m in metrics.items()] + marked()
    flags_of = lambda t: [f for f in outcome.flags if f.startswith(f"{t}:")]  # noqa: E731
    return [row(t, v["metric"], v["value"], flags_of(t), len(failed)) for t, v in outcome.values.items()] + marked()


def latest(results: Path) -> dict[str, dict]:
    """The latest row per run_id: a later row replaces an earlier one."""
    out = {}
    if results.is_file():
        for line in open(results, encoding="utf-8"):
            r = json.loads(line)
            out[r["run_id"]] = r
    return out


def flag_configured_differently(rows: list[dict]) -> list[str]:
    """A table mixing config hashes is flagged; the flag never voids a score (R-111)."""
    by = defaultdict(set)
    for r in rows:
        by[(r["task_set"], r["target"], r.get("metric"))].add(r["config_hash"])
    return [f"{k}: configured differently" for k, v in by.items() if len(v) > 1]
