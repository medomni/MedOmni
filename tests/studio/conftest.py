"""A small built dummy workspace for Studio's tests: a copy of the dummy-mimic package, its atoms and a results file.

Everything is generated here; no real data, Docker or network (the T1 guard is on). The package is copied so the tests
can edit its labels and templates; `find_package` hands that copy out by name.
"""
import json
import shutil
import uuid
from pathlib import Path

import pytest
import yaml

from medomni.core.families.dummy.datasets import make_dataset
from medomni.core.testing import DATASETS

PAIR = "dummy-mimic_aki@n10"
RUN = "run-1"


def _copy_package(root: Path) -> Path:
    pkg = root / "bench/datasets/dummy-mimic"
    shutil.copytree(DATASETS / "dummy-mimic", pkg)
    labels = yaml.safe_load((pkg / "labels.yaml").read_text())
    for rule in labels.values():
        rule["question"] = "Does the patient develop this outcome?"
    (pkg / "labels.yaml").write_text(yaml.safe_dump(labels, sort_keys=False))
    co = pkg / "tasks/dummy-mimic_aki/cohorts"
    cohort = yaml.safe_load((co / "n4.yaml").read_text())
    cohort["select"]["n"] = 10
    (co / "n10.yaml").write_text(yaml.safe_dump(cohort, sort_keys=False))
    (co / "n4.yaml").unlink()
    (pkg / "tasks/dummy-mimic_aki/template.yaml").write_text(
        (pkg / "tasks/dummy-mimic_aki/template.yaml").read_text().replace("{{ targets }}", "the targets"))
    return pkg


def _run_records(ws_path: dict) -> None:
    """A results file with one run and its score, shaped by the contracts in `core/contracts/run.py`."""
    ref = {"kind": "agent", "name": "replay"}
    manifest = json.loads((Path(ws_path["tasks"]) / "atomtasks/_content" / PAIR / "manifest.json").read_text())
    h = manifest["config_hash"]["encoders"]
    records = [
        {"kind": "run", "run_id": RUN, "release": "0.3.0", "task_set": "dummy/smoke", "task": PAIR, "task_version": "1.0",
         "config_hash": h, "intelligence": ref, "model_served": "replay", "api_cost": 0.5,
         "agent": {"arm": "encoders", "files_opened": ["/workspace/data/tables/labevents.csv"]}},
        {"kind": "score", "run_id": RUN, "release": "0.3.0", "task_set": "dummy/smoke", "task_set_hash": "a" * 64, "target": "aki",
         "task_version": "1.0", "config_hash": h, "arm": "encoders", "n_atoms": 10, "n_failed": 0, "intelligence": ref, "metric": "auc", "value": 0.75},
    ]
    Path(ws_path["results"]).write_text("".join(json.dumps(r) + "\n" for r in records))
    run = Path(ws_path["runs"]) / RUN
    run.mkdir(parents=True)
    pred = {"run_id": RUN, "atom": "a", "target": "aki", "value": 0.5, "intelligence": ref}
    (run / "predictions.jsonl").write_text(json.dumps(pred) + "\n")
    job = run / "job-1" / "dummy-mimic_aki__1__n10"
    (job / "verifier").mkdir(parents=True)
    (job / "result.json").write_text(json.dumps({"finished_at": "2150-01-01T00:00:00+00:00", "exception_info": None}))
    (job / "verifier/gateway_usage.json").write_text(json.dumps({"calls": [
        {"encoder_id": "e__one", "outcome": "healthy"}, {"encoder_id": "e__one", "outcome": "declared"},
        {"encoder_id": "e__two", "outcome": "crash"}]}))


@pytest.fixture(scope="session", autouse=True)
def package(t1_guard):
    pkg = _copy_package(t1_guard / f"pkg-{uuid.uuid4().hex[:6]}")
    mp = pytest.MonkeyPatch()
    import medomni.core.loading as loading

    real = loading.find_package
    mp.setattr(loading, "find_package", lambda name: pkg if str(name) == "dummy-mimic" else real(name))
    yield pkg
    mp.undo()


@pytest.fixture(scope="session")
def built(t1_guard, package):
    """(workspace config, built pair): the dummy dataset built under encoders and no-perception, with one run."""
    from medomni.bench import build
    from medomni.core import workspace

    root = t1_guard / "studio"
    copy = make_dataset(package, root / "raw", subjects=40)
    fields = {"cache": str(root / "cache"), "tasks": str(root / "tasks"), "runs": str(root / "runs"), "results": str(root / "results.jsonl"),
              "keys_file": str(root / "keys.env")}
    text = f"datasets: {{dummy-mimic: {{path: {copy.root}}}}}\n" + "".join(f"{k}: {v}\n" for k, v in fields.items())
    (Path(workspace.home()) / "workspace.yaml").write_text(text)
    ws = workspace.load()
    build.build([PAIR], ["encoders", "no-perception"], ws=ws, stream=open("/dev/null", "w"))
    _run_records(fields)
    return ws, PAIR
