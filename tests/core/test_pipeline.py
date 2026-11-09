"""Check 7 (R-67): every Core piece on a dummy dataset, in order, for two users in fresh workspaces.

workspace -> `medomni cache build` (loading into the cache) -> recipes -> toy build (atoms) -> family checks and a
converter -> folder hashes and the config hash -> predictions; then the second user, `cache verify`, `cache gc`.

The toy build is test code standing in for Bench's Build (Stage 3), so nothing here is imported from a project.
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
from medomni.core.cache import Cache, verify
from medomni.core.cli import main
from medomni.core.families.check import conforms
from medomni.core.families.converters import load as load_converters
from medomni.core.families.dummy.datasets import make_dataset
from medomni.core.recipes import check_package
from medomni.core.testing import DATASETS

from .test_converters import DUMMY
from .test_plugins import make_dist

DATASET = "dummy-mimic"
PKG = DATASETS / DATASET
TASK = PKG / "tasks/dummy-mimic_aki"
PAIR = "dummy-mimic_aki@n4"
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


# ---------------------------------------------------------------- the toy build (stands in for Bench's Build)

def _t(s):
    return datetime.fromisoformat(s) if s else None


def _offset(text):
    n, unit = text.split()
    return timedelta(**{unit if unit.endswith("s") else unit + "s": float(n)})


def _label(lab, events, anchor):
    lo = anchor if lab.from_ == "anchor" else None
    hi = anchor + _offset(lab.to.split("+")[1].strip()) if "+" in (lab.to or "") else None
    inside = [e for e in events if e["time"] and (lo is None or _t(e["time"]) >= lo) and (hi is None or _t(e["time"]) <= hi)]
    if lab.exists:
        return int(any(re.search(lab.exists, e["code"]) for e in inside))
    vals = [e["numeric_value"] for e in inside if e["code"] == lab.value and e["numeric_value"] is not None]
    return (max(vals) >= lab.x) * 1 if vals else None


def toy_build(events_path, raw_root, tasks_root, convert):
    import pyarrow.parquet as pq

    template = c.load(TASK / "template.yaml", c.TaskTemplate)
    cohort = c.load(TASK / "cohorts/n4.yaml", c.Cohort)
    labels = c.load(PKG / "labels.yaml", c.LabelLibrary).root
    targets = {t.name: labels[t.label.split(":", 1)[1]] for t in template.targets}
    guard = [g for lab in targets.values() for g in lab.guard.codes]
    by_subject = {}
    for e in pq.read_table(events_path).to_pylist():
        by_subject.setdefault(e["subject_id"], []).append(e)
    pool = []
    for s, ev in sorted(by_subject.items()):
        adm = sorted(_t(e["time"]) for e in ev if e["code"] == cohort.anchor.event)
        if not adm:
            continue
        anchor = adm[0] + _offset(cohort.anchor.plus)
        before = [e for e in ev if e["time"] is None or _t(e["time"]) <= anchor]
        if not any(e["code"].startswith("FILE//cxr-radiograph-2d") for e in before):
            continue
        values = {n: _label(lab, ev, anchor) for n, lab in targets.items()}
        if values["aki"] is None:
            continue
        pool.append((s, anchor, values, before))
    k = cohort.draw.n // 2  # balanced over the two classes of draw.by
    drawn = []
    for cls in (0, 1):
        ranked = sorted((p for p in pool if p[2][cohort.draw.by[0]] == cls),
                        key=lambda p: hashlib.sha256(f"{cohort.draw.seed}|{p[0]}|{p[1].isoformat()}".encode()).hexdigest())
        drawn += ranked[:k]
    pair_dir = tasks_root / "agent" / PAIR
    answers = []
    for s, anchor, values, before in sorted(drawn):
        atom = pair_dir / s
        (atom / "data" / "files").mkdir(parents=True)
        (atom / "task.toml").write_text(f'template = "{template.template_id}"\ncohort = "n4"\npatient = "{s}"\n')
        (atom / "instruction.md").write_text(template.agent.instruction.replace("{{ targets }}", ", ".join(targets)) + "\n")
        kept = [e for e in before if not e["code"].startswith("FILE//") and not any(re.search(g, e["code"]) for g in guard)]
        with open(atom / "data" / "events.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(c.dataset.EVENT_COLUMNS), extrasaction="ignore", lineterminator="\n")
            w.writeheader()
            w.writerows(kept)
        for e in (e for e in before if e["code"].startswith("FILE//")):
            src = raw_root / e["path"]
            for part in (sorted(src.parent.glob(src.stem + ".*")) if src.suffix == ".hea" else [src]):
                shutil.copyfile(part, atom / "data" / "files" / part.name)  # copied, never linked
        convert(s, atom / "data" / "files")
        answers.append({"atom": f"{PAIR}/{s}", **values})
    parent = tasks_root / "_parents" / PAIR  # answers never sit in an atom
    parent.mkdir(parents=True)
    (parent / "answers.json").write_text(json.dumps(answers, indent=1, sort_keys=True) + "\n")
    return pair_dir


# ---------------------------------------------------------------- one user, steps 1-6

def user(tmp_path, name, monkeypatch):
    home = tmp_path / name
    data = make_dataset(PKG, home / "data", subjects=10, seed=0)  # each user's own copy of the same dataset version
    cfg = {"datasets": {DATASET: {"path": str(data.root)}}, "cache": str(home / "cache"),
           "tasks": str(home / "atomtasks"), "runs": str(home / "runs"), "results": str(home / "results.jsonl"),
           "keys_file": str(home / "keys.env")}
    (home / "workspace.yaml").write_text(yaml.safe_dump(cfg))
    monkeypatch.setenv("MEDOMNI_HOME", str(home))
    ws = c.load(home / "workspace.yaml", c.WorkspaceConfig)  # step 1
    assert ws.datasets[DATASET].path == str(data.root)

    assert main(["cache", "build", DATASET]) == 0  # step 2: verify, read, rules, write, check, into the cache
    assert main(["cache", "build", DATASET]) == 0  # the same inputs: the same entry, left alone
    cache = Cache(Path(ws.cache))
    (entry,) = [e for e in cache.entries() if e.meta.step == "events"]
    assert verify(entry) == [] and entry.meta.rows["events"] > 0

    assert check_package(PKG) == []  # step 3: recipes load through their models and cross-references resolve

    conv = load_converters().found["npy-to-edf"]  # the test's dummy converter, beside Core's h5-to-edf
    fam = families.get("spo2-series-10hz-pct", REPO)
    converted = {}

    def convert(subject, out_dir):  # one file per atom goes through the converter, cached by its version
        src = home / "extra" / f"{subject}.npy"
        src.parent.mkdir(parents=True, exist_ok=True)
        rng = np.random.default_rng(int(subject) % 1000)
        np.save(src, (95 + rng.integers(-2, 3, size=(1, 300))).astype(np.int16))
        e, _ = cache.create(DATASET, f"convert-{conv.name}", conv.version, {"family": fam.id},
                            [(f"extra/{subject}.npy", hashing.sha256_file(src))],
                            lambda d: (conv.convert(src, fam, d / "spo2.edf"), {"files": 1})[1])
        shutil.copyfile(e.path / "spo2.edf", out_dir / "spo2.edf")
        converted[subject] = e

    pair_dir = toy_build(entry.path / "events.parquet", data.root, Path(ws.tasks), convert)  # step 4
    atoms = sorted(p for p in pair_dir.iterdir() if p.is_dir())
    assert len(atoms) == 4

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
                f.write(json.dumps({"run_id": "toy-run", "atom": f"{PAIR}/{a.name}", "target": t, "value": 0.5,
                                    "intelligence": {"kind": "agent", "name": "toy"}}) + "\n")
    assert len(c.load_lines(run / "predictions.jsonl", c.PredictionRecord)) == 8
    return {"home": home, "cache": cache, "entry": entry, "data": data, "pair": pair_dir, "convert": convert,
            "atoms": fps, "set": hashing.dir_hash(pair_dir),
            "keys": sorted((e.meta.step, e.meta.key, e.meta.content_hash) for e in cache.entries())}


def test_core_end_to_end(tmp_path, monkeypatch, site, capsys):
    a = user(tmp_path, "alice", monkeypatch)
    assert all(len(h) == 64 for h in a["atoms"].values()) and len(a["set"]) == 64

    b = user(tmp_path, "bob", monkeypatch)  # step 7: a second user, a fresh workspace
    assert b["keys"] == a["keys"]  # same cache keys and content hashes (R-39)
    assert b["atoms"] == a["atoms"] and b["set"] == a["set"]  # the same built files
    from medomni.core.contracts import DatasetConfig, load

    release = load(PKG / "dataset.yaml", DatasetConfig).description.version
    configs = {p.relative_to(REPO).as_posix(): p for p in (TASK / "template.yaml", TASK / "cohorts/n4.yaml", PKG / "labels.yaml")}
    cfg = hashing.config_hash(configs, dataset_release=release, medomni_release="0.3.0")
    assert cfg.startswith("cfg1:")  # the config hash depends on config files and releases only (R-111), not the workspace

    monkeypatch.setenv("MEDOMNI_HOME", str(a["home"]))  # step 8: verify catches one changed value
    capsys.readouterr()
    assert main(["cache", "verify"]) == 0
    import pyarrow as pa
    import pyarrow.parquet as pq

    events = a["entry"].path / "events.parquet"
    rows = pq.read_table(events).to_pylist()
    drawn = set(a["atoms"])
    i = next(n for n, r in enumerate(rows) if r["subject_id"] in drawn and r["code"].startswith("VITAL//"))
    rows[i]["numeric_value"] += 1.0
    pq.write_table(pa.Table.from_pylist(rows, schema=pq.read_schema(events)), events, compression="zstd",
                   use_dictionary=False, write_statistics=False)
    assert main(["cache", "verify"]) == 1
    assert f"FAIL  {a['entry'].name}" in capsys.readouterr().out
    rebuilt = toy_build(events, a["data"].root, a["home"] / "rebuilt", a["convert"])
    changed = {p.name for p in rebuilt.iterdir() if p.is_dir() and hashing.dir_hash(p) != a["atoms"].get(p.name)}
    assert changed == {rows[i]["subject_id"]}

    monkeypatch.setattr(cache_mod, "CORE_STEPS", {"events": "2"})  # step 9: a new loading version retires the entry
    assert main(["cache", "gc", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert a["entry"].name.split("/", 1)[1] in out and "1 folder(s) to remove" in out
    assert main(["cache", "gc"]) == 0
    assert not a["entry"].path.exists()
    assert {e.meta.step for e in a["cache"].entries()} == {"convert-npy-to-edf"}
