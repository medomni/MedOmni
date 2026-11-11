"""Check 7 (R-67): every Core piece on a dummy dataset, in order, for two users in fresh workspaces.

workspace -> `medomni cache build` (loading into the cache) -> a toy builder writes Core's built-task contract (atoms)
-> Core's task checks, family checks and a converter -> folder hashes and the config hash -> predictions; then the
second user, a changed value, `cache gc`, and the same build with no cache (rule 1 of the Cache page, R-155).

The toy builder is test code standing in for any builder (R-142): its rules are code, so Core reads no recipe,
template or cohort (R-147), and nothing here is imported from a project.
"""
import csv
import hashlib
import json
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
import yaml

from medomni.core import cache as cache_mod
from medomni.core import contracts as c
from medomni.core import families, hashing, plugins
from medomni.core.builders import TaskBuilder
from medomni.core.loading import build as load_dataset
from medomni.core.cli import main
from medomni.core.families.check import conforms
from medomni.core.families.converters import load as load_converters
from medomni.core.families.dummy.datasets import make_dataset
from medomni.core.tasks import asset, layout
from medomni.core.tasks.checks import task_checks
from medomni.core.testing import DATASETS

from .test_converters import DUMMY
from .test_dummy import PLANTS
from .test_plugins import make_dist

DATASET = "dummy-mimic"
PKG = DATASETS / DATASET  # Core's loader-only package
TASK, ARM = "toy-aki", "toy"
REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def site(tmp_path, monkeypatch):
    """The dummy family converter, installed as a plug-in (`npy-to-edf`)."""
    import sys

    root = tmp_path / "site"
    root.mkdir()
    monkeypatch.syspath_prepend(str(root))
    make_dist(root, "medomni-npy", "fake_npy", {plugins.CONVERTERS: {"npy-to-edf": "fake_npy:CONVERTER"}})
    (root / "fake_npy" / "__init__.py").write_text(DUMMY)
    yield root
    for m in [m for m in sys.modules if m.startswith("fake_")]:
        del sys.modules[m]


# ---------------------------------------------------------------- the toy builder (stands in for any builder)

RULES = {"anchor": "ADMISSION", "plus_hours": 24, "needs_file": "cxr-radiograph-2d", "n": 4, "seed": 7,
         "targets": {"aki": "auc", "creat_high": "auc"}}  # its whole config: the labels are the plants below
LABELS = PLANTS[DATASET]
GUARD = ("^DIAGNOSIS//ICD//N17", "^LAB//90001$")  # codes that would give a target away


class ToyBuilder(TaskBuilder):
    name, version = "toy", "1"

    def config_files(self, task, arm, variant):
        return {"rules": json.dumps(RULES, sort_keys=True).encode()}

    def build(self, tasks, arms, workspace):
        raise NotImplementedError("the test calls toy_build with its events and converter")


def _t(s):
    return datetime.fromisoformat(s) if s else None


def _window(text, anchor):
    if text in (None, "any"):
        return None
    m = re.match(r"^anchor(?:\s*\+\s*(\d+) days)?$", text)
    return anchor + timedelta(days=int(m.group(1) or 0))


def _label(lab, events, anchor):
    lo, hi = _window(lab.from_, anchor), _window(lab.to, anchor)
    inside = [e for e in events if e["time"] and (lo is None or _t(e["time"]) >= lo) and (hi is None or _t(e["time"]) <= hi)]
    if lab.exists:
        return int(any(re.search(lab.exists, e["code"]) for e in inside))
    vals = [e["numeric_value"] for e in inside if e["code"] == lab.value and e["numeric_value"] is not None]
    return int(max(vals) >= lab.x) if vals else None


def _contract_files(atom: Path, anchor: datetime) -> None:
    for sub in ("environment", "tests"):
        (atom / sub).mkdir(parents=True, exist_ok=True)
    (atom / "task.toml").write_text(f'version = "1.0"\n\n[atom]\nprediction_time = "{anchor.isoformat(sep=" ")}"\n')
    (atom / "environment/Dockerfile").write_text(asset("environment", "Dockerfile"))
    (atom / "environment/docker-compose.yaml").write_text(yaml.safe_dump(
        {"services": {"main": {"networks": ["n"]}}, "networks": {"n": {"internal": True}}}))
    (atom / "tests/format_check.py").write_text(asset("formatcheck", "format_check.py"))
    (atom / "tests/test.sh").write_text(asset("formatcheck", "test.sh"))
    (atom / "tests/expected.json").write_text(json.dumps({"targets": sorted(RULES["targets"])}))


def toy_build(events_path, raw_root, tree, convert):
    """Select, stage and write the task in Core's built-task contract (R-143). Returns the arm's atom folder."""
    import pyarrow.parquet as pq

    by_subject = {}
    for e in pq.read_table(events_path).to_pylist():
        by_subject.setdefault(e["subject_id"], []).append(e)
    pool = []
    for s, ev in sorted(by_subject.items()):
        adm = sorted(_t(e["time"]) for e in ev if e["code"] == RULES["anchor"])
        if not adm:
            continue
        anchor = adm[0] + timedelta(hours=RULES["plus_hours"])
        before = [e for e in ev if e["time"] is None or _t(e["time"]) <= anchor]
        if not any(e["code"] == "FILE//" + RULES["needs_file"] for e in before):
            continue
        values = {n: _label(LABELS[n], ev, anchor) for n in RULES["targets"]}
        if values["aki"] is None:
            continue
        pool.append((s, anchor, values, before))
    k = RULES["n"] // 2  # balanced over aki's two classes
    drawn = []
    for cls in (0, 1):
        ranked = sorted((p for p in pool if p[2]["aki"] == cls),
                        key=lambda p: hashlib.sha256(f"{RULES['seed']}|{p[0]}|{p[1].isoformat()}".encode()).hexdigest())
        drawn += ranked[:k]
    toy = ToyBuilder()
    atoms, answers = [], []
    for s, anchor, values, before in sorted(drawn):
        name = str(s)  # one task per tree here, so the subject names its atom
        atom = layout.atom_dir(tree, ARM, None, name)
        (atom / "data" / "files").mkdir(parents=True)
        _contract_files(atom, anchor)
        (atom / "instruction.md").write_text(f"Predict {', '.join(RULES['targets'])} for this patient from the record up "
                                             "to the prediction time.\n")
        kept = [e for e in before if not e["code"].startswith("FILE//") and not any(re.search(g, e["code"]) for g in GUARD)]
        with open(atom / "data" / "events.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(c.dataset.EVENT_COLUMNS), extrasaction="ignore", lineterminator="\n")
            w.writeheader()
            w.writerows(kept)
        refs = []
        for e in (e for e in before if e["code"].startswith("FILE//")):
            src = raw_root / e["path"]
            for part in (sorted(src.parent.glob(src.stem + ".*")) if src.suffix == ".hea" else [src]):
                shutil.copyfile(part, atom / "data" / "files" / part.name)  # copied, never linked
            refs.append({"path": f"data/files/{src.name}", "t_start": e["time"]})
        (atom / "data" / "references.jsonl").write_text("".join(json.dumps(r) + "\n" for r in refs))
        convert(s, atom / "data" / "files")
        atoms.append({"atom": name, "subject": str(s), "prediction_time": anchor.isoformat(sep=" ")})
        answers += [(str(s), t, values[t], RULES["targets"][t]) for t in RULES["targets"] if values[t] is not None]
    content = layout.content_dir(tree, TASK)  # answers never sit in an atom
    content.mkdir(parents=True)
    (content / "content.json").write_text(json.dumps({"version": "1.0", "atoms": atoms, "targets": [
        {"name": t, "metric": m} for t, m in RULES["targets"].items()]}, indent=1, sort_keys=True) + "\n")
    with open(content / "answers.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(c.built.ANSWERS)
        w.writerows(answers)
    release = c.load(PKG / "dataset.yaml", c.DatasetConfig).description.version
    cfg = hashing.config_hash(toy.config_files(TASK, ARM, None), dataset_release=release, medomni_release="0.3.0")
    (content / "manifest.json").write_text(json.dumps({"config_hash": {ARM: cfg}, "builder": toy.label}) + "\n")
    return tree / ARM


# ---------------------------------------------------------------- one user, steps 1-6

def user(tmp_path, name, monkeypatch, cache=None):
    home = tmp_path / name
    data = make_dataset(PKG, home / "data", subjects=10, seed=0, plant=LABELS)  # each user's own copy of the same dataset version
    cfg = {"datasets": {DATASET: {"path": str(data.root)}}, "cache": cache or str(home / "cache"),
           "tasks": str(home / "atomtasks"), "runs": str(home / "runs"), "results": str(home / "results.jsonl"),
           "keys_file": str(home / "keys.env")}
    (home / "workspace.yaml").write_text(yaml.safe_dump(cfg))
    monkeypatch.setenv("MEDOMNI_HOME", str(home))
    ws = c.load(home / "workspace.yaml", c.WorkspaceConfig)  # step 1
    assert ws.datasets[DATASET].path == str(data.root)

    assert main(["cache", "build", DATASET]) == 0  # step 2: verify, read, rules, write, check, into the cache
    assert main(["cache", "build", DATASET]) == 0  # the same inputs: the same result, left alone
    cache = cache_mod.of(ws)  # the workspace's backend
    entry, _ = load_dataset(PKG, data.root, cache, DATASET)
    assert entry.step == "events" and entry.rows["events"] > 0

    conv = load_converters().found["npy-to-edf"]  # the test's dummy converter, beside Core's h5-to-edf
    fam = families.get("spo2-series-10hz-pct", REPO)
    converted = {}

    def convert(subject, out_dir):  # one file per atom goes through the converter, cached by its version
        src = home / "extra" / f"{subject}.npy"
        src.parent.mkdir(parents=True, exist_ok=True)
        rng = np.random.default_rng(int(subject) % 1000)
        np.save(src, (95 + rng.integers(-2, 3, size=(1, 300))).astype(np.int16))
        e, _ = cache.run(DATASET, f"convert-{conv.name}", conv.version, {"family": fam.id},
                            [(f"extra/{subject}.npy", hashing.sha256_file(src))],
                            lambda d: (conv.convert(src, fam, d / "spo2.edf"), {"files": 1})[1])
        shutil.copyfile(e.path / "spo2.edf", out_dir / "spo2.edf")
        converted[subject] = e

    tree = layout.tree(ws)
    pair_dir = toy_build(entry.path / "events.parquet", data.root, tree, convert)  # step 3: the built-task contract
    atoms = sorted(p for p in pair_dir.iterdir() if p.is_dir())
    assert len(atoms) == 4
    assert task_checks(tree, TASK, [ARM]) == []  # step 4: Core's checks over built output alone (R-143)
    content = c.load(layout.content_dir(tree, TASK) / "content.json", c.BuiltContent)
    assert sorted(a.atom for a in content.atoms) == [a.name for a in atoms]

    for atom in atoms:  # step 5: every staged family file passes its family's checks
        for f in (atom / "data/files").iterdir():
            fid = {".png": "cxr-radiograph-2d", ".edf": "spo2-series-10hz-pct"}.get(f.suffix)
            if f.suffix == ".hea":
                fid = "ecg-12lead-500hz-mv" if "ecg" in str(next(data.root.rglob(f.name))) else "abp-waveform-125hz-mmhg"
            if fid:
                assert conforms(families.get(fid, REPO), f) == [], f

    # no planted answer (canary) reaches an atom (R-47, the label guards)
    for atom in atoms:
        text = (atom / "data/events.csv").read_text() + (atom / "instruction.md").read_text()
        for label in data.planted["labels"].values():
            for ev in label["events"]:
                if ev["subject"] == atom.name:
                    assert ev["code"] not in text, (atom.name, ev)

    fps = {a.name: hashing.dir_hash(a) for a in atoms}  # step 6: a test compares built folders directly (R-111)
    run = home / "runs" / "toy-run"
    run.mkdir(parents=True)
    with open(run / "predictions.jsonl", "w") as f:  # the handoff to the scorer (R-77)
        for a in atoms:
            for t in ("aki", "creat_high"):
                f.write(json.dumps({"run_id": "toy-run", "atom": f"{TASK}/{a.name}", "target": t, "value": 0.5,
                                    "intelligence": {"kind": "agent", "name": "toy"}}) + "\n")
    assert len(c.load_lines(run / "predictions.jsonl", c.PredictionRecord)) == 8
    return {"home": home, "cache": cache, "entry": entry, "data": data, "pair": pair_dir, "convert": convert,
            "atoms": fps, "set": hashing.dir_hash(pair_dir),
            "keys": sorted([entry.key] + [e.key for e in converted.values()])}


def test_core_end_to_end(tmp_path, monkeypatch, site, capsys):
    a = user(tmp_path, "alice", monkeypatch)
    assert all(len(h) == 64 for h in a["atoms"].values()) and len(a["set"]) == 64

    b = user(tmp_path, "bob", monkeypatch)  # step 7: a second user, a fresh workspace
    assert b["keys"] == a["keys"]  # same cache keys: built from the step's arguments alone (R-155)
    assert b["atoms"] == a["atoms"] and b["set"] == a["set"]  # the same built files
    manifests = [c.load(layout.content_dir(layout.tree(c.load(u["home"] / "workspace.yaml", c.WorkspaceConfig)), TASK)
                        / "manifest.json", c.BuiltManifest) for u in (a, b)]
    assert manifests[0] == manifests[1] and manifests[0].config_hash[ARM].startswith("cfg1:")  # config and releases only
    assert manifests[0].builder == "toy/1"  # (R-111), not the workspace

    monkeypatch.setenv("MEDOMNI_HOME", str(a["home"]))  # step 8: one changed value changes that patient's atom only
    capsys.readouterr()
    import pyarrow as pa
    import pyarrow.parquet as pq

    events = a["entry"].path / "events.parquet"
    rows = pq.read_table(events).to_pylist()
    drawn = set(a["atoms"])
    i = next(n for n, r in enumerate(rows) if r["subject_id"] in drawn and r["code"].startswith("VITAL//"))
    rows[i]["numeric_value"] += 1.0
    pq.write_table(pa.Table.from_pylist(rows, schema=pq.read_schema(events)), events, compression="zstd",
                   use_dictionary=False, write_statistics=False)
    rebuilt = toy_build(events, a["data"].root, a["home"] / "rebuilt" / "atomtasks", a["convert"])
    changed = {p.name for p in rebuilt.iterdir() if p.is_dir() and hashing.dir_hash(p) != a["atoms"].get(p.name)}
    assert changed == {rows[i]["subject_id"]}

    monkeypatch.setattr(cache_mod, "CORE_STEPS", {"events": "2"})  # step 9: a new loading version retires the entry
    assert main(["cache", "gc", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert a["entry"].name.split("/", 1)[1] in out and "1 folder(s) to remove" in out
    assert main(["cache", "gc"]) == 0
    assert not a["entry"].path.exists()
    assert {e.step for e in a["cache"].results()} == {"convert-npy-to-edf"}

    monkeypatch.setattr(cache_mod, "CORE_STEPS", {"events": "1"})
    n = user(tmp_path, "nora", monkeypatch, cache={"backend": "none"})  # step 10: no cache, the same build (rule 1)
    assert n["atoms"] == a["atoms"] and n["set"] == a["set"] and n["keys"] == a["keys"]
    assert not (n["home"] / "cache").exists()
