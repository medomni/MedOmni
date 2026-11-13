"""Checks over built output alone (R-143 a): Bench runs them before every run, whoever built the task, and a builder
runs them after it writes. Each returns a list of problems naming the check and the task or atom, never a patient's values."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

import yaml

from medomni.core.contracts import ContractError
from medomni.core.contracts.built import ANSWERS, ATOM_FILES, GOLD_NAMES, BuiltContent, BuiltManifest

from . import layout
from .times import before_or_at
from .wfdb import companions


def contract_files(tree: Path, task: str) -> tuple[list[str], BuiltContent | None]:
    """The task's content files are present and follow the contract."""
    d, out, content = layout.content_dir(tree, task), [], None
    for name, model in (("content.json", BuiltContent), ("manifest.json", BuiltManifest)):
        p = d / name
        if not p.is_file():
            out.append(f"contract files: {task}: no {name}")
            continue
        try:
            obj = model.model_validate(json.loads(p.read_text(encoding="utf-8")))
        except (ValueError, ContractError) as e:
            out.append(f"contract files: {task}: {name} does not follow the built-task contract: {str(e).splitlines()[0]}")
            continue
        content = obj if name == "content.json" else content
    p = d / "answers.csv"
    if not p.is_file():
        out.append(f"contract files: {task}: no answers.csv")
    else:
        with open(p, newline="", encoding="utf-8") as f:
            head = next(csv.reader(f), [])
        if tuple(head) != ANSWERS:
            out.append(f"contract files: {task}: answers.csv's header is not {','.join(ANSWERS)}")
    return out, content


def atom_files(atom: Path) -> list[str]:
    return [f"contract files: {atom.name}: no {rel}" for rel in ATOM_FILES if not (atom / rel).is_file()]


def no_gold(atom: Path) -> list[str]:
    """No answer inside an atom: no gold-shaped file, and expected.json names the targets only."""
    out = [f"no gold: {atom.name}: {p.relative_to(atom)} is in the atom" for p in atom.rglob("*") if p.name in GOLD_NAMES]
    exp = atom / "tests/expected.json"
    if exp.is_file() and set(json.loads(exp.read_text(encoding="utf-8"))) != {"targets"}:
        out.append(f"no gold: {atom.name}: tests/expected.json holds more than the target names")
    return out


def format_check(atom: Path) -> list[str]:
    """The atom's format check runs, and accepts a submission of every target it expects."""
    exp = atom / "tests/expected.json"
    if not exp.is_file() or not (atom / "tests/format_check.py").is_file():
        return []
    targets = json.loads(exp.read_text(encoding="utf-8"))["targets"]
    with tempfile.TemporaryDirectory(prefix="medomni-format-") as tmp:
        sub = Path(tmp) / "predictions.csv"
        sub.write_text("target,prediction\n" + "".join(f"{t},0.5\n" for t in targets), encoding="utf-8")
        r = subprocess.run([sys.executable, str(atom / "tests/format_check.py"), str(sub), str(exp)],
                           capture_output=True, text=True, timeout=60)
    try:
        ok = r.returncode == 0 and json.loads(r.stdout).get("format_ok") == 1
    except ValueError:
        ok = False
    return [] if ok else [f"format check: {atom.name}: tests/format_check.py does not accept a well-formed submission"]


def _prediction_time(atom: Path):
    p = atom / "task.toml"
    if not p.is_file():
        return None
    return (tomllib.loads(p.read_text(encoding="utf-8")).get("atom") or {}).get("prediction_time") or None


def image_times(atom: Path) -> list[str]:
    """Nothing dated after the prediction time: each staged reference's `t_start` against task.toml's prediction time."""
    refs = atom / "data/references.jsonl"
    if not refs.exists():
        return []
    b, out = _prediction_time(atom), []
    for line in refs.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["path"].startswith("/"):
            out.append(f"nothing after the prediction time: {atom.name}: an absolute path in references.jsonl")
        elif b and r.get("t_start") and not before_or_at(r["t_start"], b):
            out.append(f"nothing after the prediction time: {atom.name}: {r['path']} is dated after it")
    return out


def recordings(atom: Path) -> list[str]:
    """Complete recordings: each staged WFDB header's companion files are staged too (read through refs.map.json)."""
    rm = atom / "environment/refs.map.json"
    if not rm.exists():
        return []
    mapping = json.loads(rm.read_text(encoding="utf-8"))
    staged, out = set(mapping.values()), []
    for rel, ab in mapping.items():
        if not rel.endswith(".hea"):
            continue
        try:
            missing = [c.name for c in companions(Path(ab)) if str(c) not in staged]
        except RuntimeError as e:
            missing = [str(e)]
        if missing:
            out.append(f"complete recordings: {atom.name}: {rel} misses {missing}")
    return out


def network(atom: Path) -> list[str]:
    """A closed network: one internal network, and every service on it."""
    p = atom / "environment/docker-compose.yaml"
    if not p.is_file():
        return []
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    nets = doc.get("networks") or {}
    out = []
    if len(nets) != 1 or not all((n or {}).get("internal") for n in nets.values()):
        out.append(f"closed network: {atom.name}: not one internal network")
    for name, s in doc["services"].items():
        if s.get("networks") != list(nets):
            out.append(f"closed network: {atom.name}: service {name} is not on the one internal network")
    return out


def atom_checks(atom: Path) -> list[str]:
    return atom_files(atom) + no_gold(atom) + format_check(atom) + image_times(atom) + recordings(atom) + network(atom)


def task_checks(tree: Path, task: str, arms: list[str]) -> list[str]:
    """Every check over one built task under the given arms, with all their built variants."""
    out, content = contract_files(tree, task)
    if content is None:
        return out
    for arm in arms:
        variants = layout.variants(tree, task, arm)
        if not variants:
            out.append(f"contract files: {task}: not built under {arm}")
        for v in variants:
            for a in content.atoms:
                d = layout.atom_dir(tree, arm, v, a.atom)
                out += atom_checks(d) if d.is_dir() else [f"contract files: {task}: atom {a.atom} not built under {arm}{'/' + v if v else ''}"]
    return out
