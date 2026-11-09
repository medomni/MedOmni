"""Part 2, T3: each shipped package, loaded from the real copy, gives v0.2's gold on every n20 patient.

The event tables are written to `<workspace>/scratch-p2/<dataset>/` on first use, and reused (delete them to reload;
a load takes 6 to 15 minutes). Needs v0.2.1's checkout, the raw copies and a workspace: T4. Prints counts only.
    MEDOMNI_STAGE3_WORKSPACE=<workspace.yaml> pytest -m baseline tests/bench/test_gold_baseline.py -s
"""
import csv
import os
from collections import Counter, defaultdict
from pathlib import Path

import pytest

pytestmark = [pytest.mark.baseline, pytest.mark.data]

REPO = Path(__file__).resolve().parents[2]
V02 = Path(os.environ.get("MEDOMNI_V02", "<v0.2 checkout>"))
WORKSPACE = Path(os.environ.get("MEDOMNI_STAGE3_WORKSPACE", "<workspace>/workspace.yaml"))
GOLD_ROWS = {"bdsp": 380, "mimic-iv": 260, "aireadi": 660}


def _same(ours, gold: str) -> bool:
    if ours is None or gold == "":  # no value on either side is the same answer
        return ours is None and gold == ""
    return abs(float(ours) - float(gold)) < 1e-9


@pytest.mark.parametrize("dataset", sorted(GOLD_ROWS))
def test_labels_equal_v02_gold(dataset):
    import pyarrow.parquet as pq

    from medomni.bench.build.labels import anchor, label
    from medomni.core import workspace
    from medomni.core.contracts import Cohort, LabelLibrary, TaskTemplate, load as load_contract
    from medomni.core.contracts.convert.templates import NAME_MAP
    from medomni.core.loading import load

    package = REPO / "bench/datasets" / dataset
    out = WORKSPACE.parent / "scratch-p2" / dataset
    if not (out / "events.parquet").exists():
        load(package, Path(workspace.dataset_path(workspace.load(WORKSPACE), dataset)), out)
    events = defaultdict(list)
    for row in pq.read_table(out / "events.parquet").to_pylist():
        events[row["subject_id"]].append(row)
    library = load_contract(package / "labels.yaml", LabelLibrary).root
    v02_name = {new: old for old, new in NAME_MAP.items()}
    outcome = Counter()
    for tdir in sorted((package / "tasks").glob("*/")):
        tpl = load_contract(tdir / "template.yaml", TaskTemplate)
        cohort = load_contract(tdir / "cohorts/n20.yaml", Cohort)
        targets = {t.name: t for t in tpl.targets}
        gold = V02 / "data_task/atomtasks/_parents" / f"{v02_name.get(tpl.template_id, tpl.template_id)}__n20/gold.csv"
        with open(gold, newline="") as f:
            for g in csv.DictReader(f):
                ctx = anchor(events.get(g["subject_id"], []), cohort.anchor)
                t = targets[g["target"]]
                outcome["same" if ctx and _same(label(library[t.label.split(":", 1)[1]], ctx), g["value"]) else "DIFFERS"] += 1
    print(f"\n{dataset}: gold rows {dict(outcome)}")
    assert outcome == {"same": GOLD_ROWS[dataset]}
