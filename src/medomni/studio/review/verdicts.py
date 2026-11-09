"""LLM and human verdicts, and what each binds to (R-114).

A verdict is one JSON line in `<reviews>/llm/*.jsonl` or `<reviews>/human/*.jsonl`:

    {"check": "T-CLIN.1", "instance": "<id>", "hash": "<binding>", "outcome": "pass|warn|fail", "note": "...", "by": "..."}

Human verdicts add `signed_by`. A verdict counts only while its `hash` equals the instance's binding now; otherwise it
reverts to unassessed. Bindings:

- a task: `config_hash` of its template, cohort, labels, evidence rules and dataset release (Pair.config_files), which
  leaves out the arm, so an arm change keeps a sign-off and the six ladder rungs share one;
- an encoder: its card's hash and image digest;
- a family: its file's hash and sample revision;
- a dataset package: its files except `tasks/`;
- a run: its config hash, with the number of finished runs reported beside it, never staled by it.

The MedOmni release is held fixed in a task's binding: a new release of the code does not revoke a clinician's
sign-off of an unchanged task.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from medomni.core import hashing

from .. import common
from .engine import NOT_FOR, Item
from .matrix import FAIL, NONE, PASS, WARN

TASK_RELEASE = "verdict"  # stands in for the MedOmni release in a task's binding, see above
LLM_BLOCKED = {
    "T-CLIN.4": "a clinician sign-off bound to the task config hash: only a human can satisfy it",
    "R-CLIN.4": "a human review bound to the run and task hashes: only a human can satisfy it",
    "R-ISOL.1": "needs agent trace content (patient-level): DUA: not sent to a hosted model",
    "R-ISOL.2": "needs agent trace content (patient-level): DUA: not sent to a hosted model",
    "R-ISOL.3": "needs agent trace content (patient-level): DUA: not sent to a hosted model",
}


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:12]


def task_binding(pair) -> str:
    return hashing.config_hash(pair.config_files(), dataset_release=pair.config.description.version, medomni_release=TASK_RELEASE)


def encoder_binding(edir: Path, card: dict) -> str:
    digest = (card.get("runtime") or {}).get("digest") or "none"
    return f"{_sha((edir / 'card.yaml').read_bytes())}@{digest}"


def family_binding(path: Path, fam) -> str:
    return f"{_sha(path.read_bytes())}@{str((fam.samples.revision if fam.samples else 'none'))[:10]}"


def dataset_binding(package: Path) -> str:
    exclude = tuple(f for f in hashing.files(package) if f.startswith("tasks/") or "__pycache__" in f)
    return "pkg:" + hashing.dir_hash(package, exclude)


def bindings(scope) -> dict[str, dict[str, str]]:
    """Asset letter -> {instance: binding} for every instance a verdict can bind to."""
    import yaml

    from medomni.core import families as registry
    from medomni.core.loading import find_package

    out: dict = {"D": {}, "F": {}, "P": {}, "T": {}, "R": {}}
    for ds in scope.datasets:
        try:
            out["D"][ds] = dataset_binding(find_package(ds))
        except FileNotFoundError:
            pass
    folder = registry.folder()
    for fid, fam in scope.families.items():
        out["F"][fid] = family_binding(folder / f"{fid}.yaml", fam)
    for edir in scope.encoders:
        card = yaml.safe_load((edir / "card.yaml").read_text(encoding="utf-8"))
        out["P"][common.encoder_id(edir)] = encoder_binding(edir, card)
    for pair_id in scope.pairs:
        out["T"][pair_id] = task_binding(common.load_pair(pair_id))
    runs, _ = scope.run_records
    n = len(runs)
    for r in runs:
        out["R"][r.run_id] = f"{r.config_hash}@{n}"
    return out


def _read(d: Path) -> list[dict]:
    out = []
    for p in sorted(d.glob("*.jsonl")) if d.exists() else ():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                r["_file"] = p.name
                out.append(r)
    return out


def items(reviews: Path, cells: dict, scope, bound: dict | None = None) -> list[Item]:
    """The recorded verdicts as items, then an unassessed item for every LLM or human check that has none."""
    bound = bound if bound is not None else bindings(scope)
    out, got = [], set()
    for aud, sub in (("L", "llm"), ("H", "human")):
        for r in _read(reviews / sub):
            k = str(r.get("check", ""))
            cell = cells.get(k.split(".")[0])
            if not cell or k not in cell["checks"] or aud not in cell["auditors"]:
                continue
            cur = bound.get(k[0], {}).get(r.get("instance"))
            rec = str(r.get("hash"))
            note = str(r.get("note", ""))
            if aud == "H" and not r.get("signed_by"):
                o, note = NONE, "human verdict present but unsigned"
            elif cur is None:
                o, note = NONE, "instance not in the audited scope"
            elif k[0] == "R" and cur.split("@")[0] == rec.split("@")[0]:
                o = r.get("outcome", NONE)
                if cur.split("@")[-1] != rec.split("@")[-1]:
                    note = f"[judged on {rec.split('@')[-1]} finished runs; {cur.split('@')[-1]} now] {note}"
            elif cur != rec:
                o, note = NONE, f"stale: verdict bound to {rec}, instance is now {cur}"
            else:
                o = r.get("outcome", NONE)
            if o not in (PASS, WARN, FAIL, NONE):
                o = NONE
            out.append(Item(k, aud, scope.mask.mask(str(r.get("instance"))), o, scope.mask.mask(note)[:400], f"reviews/{sub}/{r['_file']}"))
            got.add((k, aud))
    for cid, cell in cells.items():
        for k in cell["checks"]:
            if "L" in cell["auditors"] and (k, "L") not in got and (k, "L") not in NOT_FOR:
                out.append(Item(k, "L", "(all)", NONE, LLM_BLOCKED.get(k, "no LLM verdict recorded"), "reviews"))
            if "H" in cell["auditors"] and (k, "H") not in got:
                out.append(Item(k, "H", "(all)", NONE, "no signed human review bound to the current hash", "reviews"))
    return out
