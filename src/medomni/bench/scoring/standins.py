"""Stand-in agents (R-54): two answer sheets scored like a run, with no model calls, before anything runs.

- **Oracle:** every atom answers its patient's true values. Each target must score perfectly: AUC 1, QWK 1, MAE 0.
- **No information:** every atom gives one answer per target, the best one without looking at the patient: 0.5 for
  AUC, the most common class for QWK, the median for MAE. Each target must score at chance: AUC 0.5, QWK 0, and MAE
  equal to the answers' mean distance from their median.

A task that fails either has broken answers or scoring (an answer for no atom, a reversed or leaking metric), found
before a paid run. Problems name the task, target and the two scores, never a patient's value.
"""
from __future__ import annotations

import statistics
from collections import Counter
from pathlib import Path

from medomni.core.tasks import layout

from . import Refused, read_gold, score_targets

TOL = 1e-4  # the metrics round to 4 places


def _no_information(metric: str, answers: list[float]) -> tuple[float, float | None]:
    """(the constant answer, the score it must get)."""
    if metric == "auc":
        return 0.5, 0.5
    if metric == "qwk":
        return Counter(answers).most_common(1)[0][0], 0.0
    m = statistics.median(answers)
    return m, round(sum(abs(a - m) for a in answers) / len(answers), 4)


PERFECT = {"auc": 1.0, "qwk": 1.0, "mae": 0.0}


def problems(tree: Path, task: str) -> list[str]:
    metrics, gold, subject_of = read_gold(layout.content_dir(tree, task))
    subjects = set(subject_of.values())
    out = [f"stand-in agents: {task}: target {t} has answers for {len(set(g) - subjects)} subject(s) with no atom"
           for t, g in sorted(gold.items()) if set(g) - subjects]
    if out:
        return out
    oracle = {s: {t: g[s] for t, g in gold.items() if s in g} for s in subjects}
    constants = {t: _no_information(metrics[t], list(g.values())) for t, g in gold.items()}
    blind = {s: {t: c for t, (c, _) in constants.items() if s in gold[t]} for s in subjects}
    for name, preds, want in (("oracle", oracle, {t: PERFECT[metrics[t]] for t in gold}),
                              ("no-information", blind, {t: e for t, (_, e) in constants.items()})):
        try:
            got = score_targets(metrics, gold, preds).values
        except Refused as e:
            out.append(f"stand-in agents: {task}: the {name} agent is refused: {e}")
            continue
        for t, v in sorted(got.items()):
            if v["value"] is None or want[t] is None:
                continue  # one-class or degenerate: the scorer flags it, nothing to compare
            if abs(v["value"] - want[t]) > TOL:
                out.append(f"stand-in agents: {task}: the {name} agent scores {t} ({v['metric']}) {v['value']}, not {want[t]}")
    return out
