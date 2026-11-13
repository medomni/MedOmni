"""R-54: the stand-in agents. True answers score perfectly and a no-information answer scores at chance, on every
task before a run; a task whose answers or scoring are broken is caught first."""
import csv
import json

import pytest

from medomni.bench import scoring
from medomni.bench.scoring import standins
from medomni.core.tasks import layout

TASK = "toy_risk@x"


def _task(tree, rows, atoms=6):
    d = layout.content_dir(tree, TASK)
    d.mkdir(parents=True)
    targets = sorted({(t, m) for _, t, _, m in rows})
    (d / "content.json").write_text(json.dumps({"version": "1.0", "targets": [{"name": t, "metric": m} for t, m in targets],
                                                "atoms": [{"atom": f"a{i}", "subject": str(i)} for i in range(atoms)]}))
    with open(d / "answers.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subject_id", "target", "value", "metric"])
        w.writerows(rows)
    return tree


def _rows():
    out = []
    for i in range(6):
        out += [(str(i), "risk", i % 2, "auc"), (str(i), "stage", i % 3, "qwk"), (str(i), "level", 10 + 3 * i, "mae")]
    return out


def test_a_sound_task_passes(tmp_path):
    assert standins.problems(_task(tmp_path, _rows()), TASK) == []


def test_an_answer_with_no_atom_is_caught(tmp_path):
    tree = _task(tmp_path, _rows() + [("99", "risk", 1, "auc")])
    (p,) = standins.problems(tree, TASK)
    assert "risk has answers for 1 subject(s) with no atom" in p


def test_a_reversed_metric_is_caught(tmp_path, monkeypatch):
    monkeypatch.setitem(scoring.METRICS, "auc", lambda pairs: round(1 - _auc(pairs), 4))  # ranks read backwards
    found = standins.problems(_task(tmp_path, _rows()), TASK)
    assert any("oracle agent scores risk (auc) 0.0, not 1.0" in p for p in found)


def test_a_leaking_metric_is_caught(tmp_path, monkeypatch):
    """A metric that scores a constant answer above chance gives information it shouldn't have."""
    monkeypatch.setitem(scoring.METRICS, "qwk", lambda pairs: 1.0)
    found = standins.problems(_task(tmp_path, _rows()), TASK)
    assert found == [f"stand-in agents: {TASK}: the no-information agent scores stage (qwk) 1.0, not 0.0"]


def test_a_one_class_target_is_left_to_the_scorer(tmp_path):
    rows = [(str(i), "risk", 1, "auc") for i in range(6)]
    assert standins.problems(_task(tmp_path, rows), TASK) == []


def _auc(pairs):
    from medomni.bench.metrics import auc

    return auc(pairs)


@pytest.mark.parametrize("bad", ["no atom", "fine"])
def test_preflight_runs_them(tmp_path, monkeypatch, bad):
    from medomni.bench import runs

    rows = _rows() + ([("99", "risk", 1, "auc")] if bad == "no atom" else [])
    tree = _task(tmp_path, rows)
    monkeypatch.setattr(runs, "task_checks", lambda tree, task, arms: [])  # the built files themselves are Core's checks
    task_set = type("S", (), {"tasks": [type("E", (), {"task": TASK})()]})()
    if bad == "no atom":
        with pytest.raises(runs.RunError, match="stand-in agents"):
            runs.preflight(tree, task_set, ["encoders"])
    else:
        runs.preflight(tree, task_set, ["encoders"])
