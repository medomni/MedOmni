"""The audit's Task cells. Task isolation reads Bench's `task check` results and never reimplements them (R-125). The
seven gates R-119 leaves to the audit are here too, each under the check it speaks to:

    vectors      T-ISOL.2   a test case for every leakage rule
    canary       T-ISOL.3   the canary is in task.toml and never in the prompt
    budget       T-CONF.3   the agent timeout and call budget match the template and the arm
    limits       P-COMP.2   (in the encoders checks) every reachable encoder's card states its limits
    famcoverage  T-COMP.2   declared families are staged; twins stage the same files
    inventory    T-COMP.2   what the atom says it staged is what is on disk, and no bind leaves it
    instr        T-CONF.3   the instruction holds its required clauses and none it must not
"""
from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import yaml

from ... import common
from ...survey.dataset import declared_families
from ..matrix import FAIL, NONE, PASS, WARN

# A problem from `bench task check` names the check it failed: this says which audit check that is (R-125)
BENCH_CHECKS = {"no answer in the evidence": "T-ISOL.2", "eligible at the prediction time": "T-CONF.3",
                "events still ahead": "T-ISOL.1", "nothing after the prediction time": "T-ISOL.1",
                "enough patients": "T-CONF.3", "answers that vary": "T-CONF.3", "complete recordings": "T-COMP.2",
                "closed network": "T-ISOL.3"}
INSTR_ABSENT = ("<!--", "This atom asks", "Evidence mode")
SUPPORT = {"inventory.json", "encoder_manifest.md", "references.jsonl"}
LEAK_TESTS = {"no answer in the evidence": "test_no_answer_in_the_evidence", "eligible": "test_eligible",
              "events still ahead": "test_events_still_ahead", "answers that vary": "test_answers_that_vary",
              "closed network": "test_closed_network", "nothing after the prediction time": "test_nothing_after_the_prediction_time",
              "complete recordings": "test_complete_recordings"}


def _bench_results(scope, sink, pair: str, arm_names=None) -> None:
    """`bench task check` on one pair: its problems become items of the checks they speak to."""
    from medomni.studio.build import run_checks

    problems = run_checks(pair, ws=scope.ws, arm_names=arm_names)
    if any("nothing built" in p for p in problems):
        for chk in set(BENCH_CHECKS.values()):
            sink.add(chk, "M", pair, NONE, "not built: Bench's task check has nothing to read", "bench task check")
        return
    grouped: dict[str, list[str]] = {}
    for p in problems:
        name = p.split(":", 1)[0]
        chk = BENCH_CHECKS.get(name)
        if chk is None:
            sink.add("T-CONF.3", "M", pair, FAIL, p, "bench task check")
            continue
        grouped.setdefault(chk, []).append(p)
    for chk in sorted(set(BENCH_CHECKS.values())):
        ps = grouped.get(chk, [])
        for p in ps:
            sink.add(chk, "M", pair, FAIL, p, "bench task check")
        if not ps:
            sink.add(chk, "M", pair, PASS, "no problem in Bench's task check", "bench task check")


def _atom_gates(scope, sink, pair_id: str, atoms: list, meta: dict) -> None:
    from medomni.studio.build.render import CANARY

    pair = common.load_pair(pair_id)
    env = pair.template.agent.environment
    from medomni.core import plugins

    budgets = {name: p.load().max_calls for name, p in plugins.resolve(plugins.ARMS).pieces.items()}
    for arm, variant, atom, d in atoms:
        instr = (d / "instruction.md").read_text(encoding="utf-8") if (d / "instruction.md").exists() else ""
        toml_path = d / "task.toml"
        sink.add("T-COMP.2", "M", atom, PASS if toml_path.exists() and instr else FAIL,
                 "task.toml and instruction present" if toml_path.exists() and instr else "task.toml or instruction.md missing", "atom files")
        toml_text = toml_path.read_text(encoding="utf-8") if toml_path.exists() else ""
        why = [w for w, bad in (("canary in instruction.md", CANARY in instr), ("canary absent from task.toml", CANARY not in toml_text)) if bad]
        sink.add("T-ISOL.3", "M", atom, FAIL if why else PASS, "; ".join(why) or "canary only in task.toml", "canary")
        bad = [x for x in INSTR_ABSENT if x in instr]
        sink.add("T-CONF.3", "M", atom, FAIL if bad else PASS, f"instruction holds {bad}" if bad else "instruction clean", "instr")
        toml = tomllib.loads(toml_text) if toml_text else {}
        timeout = (toml.get("agent") or {}).get("timeout_sec")
        problems = []
        if timeout is not None and float(timeout) != float(env.agent_timeout_sec):
            problems.append(f"agent timeout {timeout}, template says {env.agent_timeout_sec}")
        compose = (d / "environment/docker-compose.yaml").read_text(encoding="utf-8") if (d / "environment/docker-compose.yaml").exists() else ""
        want = budgets.get(arm)
        m = re.search(r"MAX_CALLS[=:]\s*(\d+)", compose)
        if want is not None and (not m or int(m.group(1)) != want):
            problems.append(f"call budget {m.group(1) if m else 'absent'}, arm says {want}")
        sink.add("T-CONF.3", "M", atom, FAIL if problems else PASS, "; ".join(problems) or "timeout and call budget match", "budget")
        _inventory(sink, atom, d, compose)
    _coverage(sink, pair_id, atoms, meta)
    _no_crossing(sink, atoms, meta)


def _no_crossing(sink, atoms: list, meta: dict) -> None:
    """An atom's inventory and its reference files name only its own patient (T-ISOL.4)."""
    own = {a["atom"]: str(a["subject"]) for a in meta["atoms"]}
    for _, _, atom, d in atoms:
        inv_path, refs = d / "data/inventory.json", d / "environment/refs.map.json"
        bad = []
        if inv_path.exists() and str(json.loads(inv_path.read_text(encoding="utf-8")).get("subject")) != own[atom]:
            bad.append("inventory names another subject")
        if refs.exists():
            others = [s for a, s in own.items() if a != atom and len(s) >= 4]
            text = refs.read_text(encoding="utf-8")
            bad += [f"reference map names another drawn patient's files ({sum(s in text for s in others)})"] if any(s in text for s in others) else []
        sink.add("T-ISOL.4", "M", atom, FAIL if bad else PASS, "; ".join(bad) or "only its own patient's files", "isolation")


def _inventory(sink, atom: str, d: Path, compose_text: str) -> None:
    inv_path = d / "data/inventory.json"
    if not inv_path.exists():
        sink.add("T-COMP.2", "M", atom, FAIL, "no data/inventory.json", "inventory")
        return
    inv = json.loads(inv_path.read_text(encoding="utf-8"))
    mapping = json.loads((d / "environment/refs.map.json").read_text(encoding="utf-8")) if (d / "environment/refs.map.json").exists() else {}
    bad = []
    listed = set()
    for fam, spec in inv["families"].items():
        for rel in spec["paths"]:
            listed.add(rel)
            if spec["kind"] == "reference":
                if rel not in mapping and not (d / "data" / rel).is_file():
                    bad.append(f"{rel} ({fam}) is not staged")
            elif not (d / "data" / rel).is_file() or (d / "data" / rel).stat().st_size == 0:
                bad.append(f"{rel} ({fam}) is not staged")
    for f in (d / "data").rglob("*"):
        rel = f.relative_to(d / "data").as_posix()
        if f.is_file() and rel not in listed and rel not in SUPPORT:
            bad.append(f"{rel} is staged but not in the inventory")
    comp = yaml.safe_load(compose_text) if compose_text else {}
    refs = set(mapping.values())
    for svc, spec in (comp or {}).get("services", {}).items():
        for vol in spec.get("volumes") or []:
            src = str(vol).split(":")[0] if isinstance(vol, str) else str((vol or {}).get("source", ""))
            if not src.startswith((".", "/")):
                continue  # a named volume
            ab = str((d / "environment" / src).resolve()) if src.startswith(".") else src
            inside = any(ab == str(d / x) or ab.startswith(str(d / x) + "/") for x in ("data", "environment", "instruction.md"))
            if not (inside or ab in refs or ab == "/var/run/docker.sock"):
                bad.append(f"service {svc} binds {src}, outside the atom and its reference map")
    sink.add("T-COMP.2", "M", atom, FAIL if bad else PASS, "; ".join(bad)[:400] or "inventory matches what is staged", "inventory")


def _coverage(sink, pair_id: str, atoms: list, meta: dict) -> None:
    """Families staged per pair, the template's declared families against them, and encoder/no-perception twins."""
    by_arm: dict = {}
    for arm, variant, atom, d in atoms:
        inv_path = d / "data/inventory.json"
        fams = set(json.loads(inv_path.read_text(encoding="utf-8"))["families"]) if inv_path.exists() else set()
        by_arm.setdefault(arm, {})[atom] = fams
    declared = set(common.load_pair(pair_id).template.input.get("families", ()))
    encoders = by_arm.get("encoders", {})
    if encoders and declared:
        staged = set().union(*encoders.values())
        missing = sorted(declared - staged)
        sink.add("T-COMP.2", "M", pair_id, FAIL if missing else PASS, f"declared but staged by no atom: {missing}" if missing else "every declared family is staged", "famcoverage")
    twins = by_arm.get("no-perception", {})
    if encoders and twins:
        diff = [a for a in encoders if a in twins and encoders[a] != twins[a]]
        sink.add("T-CONF.3", "M", pair_id, FAIL if diff else PASS, f"{len(diff)} twins stage different families" if diff else "encoders and no-perception stage the same families", "famcoverage")


def _staged_families(atoms: list) -> set[str]:
    out: set[str] = set()
    for _, _, _, d in atoms:
        inv_path = d / "data/inventory.json"
        if inv_path.exists():
            out |= set(json.loads(inv_path.read_text(encoding="utf-8"))["families"])
    return out


def _supply(sink, staged: dict, expected: dict) -> None:
    """Families a dataset supplies that no built atom stages: flagged, not failed, on a random draw (v0.2's rule)."""
    for ds, fams in staged.items():
        missing = sorted(expected.get(ds, set()) - fams)
        sink.add("T-COMP.2", "M", f"{ds}:supply", WARN if missing else PASS,
                 f"staged by no atom of the pairs audited: {missing}" if missing else "every supplied family is staged", "famcoverage")


def _vectors(sink) -> None:
    from medomni.core import plugins

    repo = plugins.find_repo()
    files = [repo / "tests/bench/test_checks.py", repo / "tests/core/test_built_tasks.py"] if repo else []  # the builder's, Core's
    if not files or not all(f.is_file() for f in files):
        sink.add("T-ISOL.2", "M", "*", NONE, "no repository test file to read", "vectors")
        return
    names = {n for f in files for n in re.findall(r"def (test_\w+)", f.read_text(encoding="utf-8"))}
    for rule, test in LEAK_TESTS.items():
        sink.add("T-ISOL.2", "M", f"rule:{rule}", PASS if test in names else FAIL,
                 f"test case {test}" if test in names else f"no test case for the rule ({test})", "vectors")


def run(scope, sink) -> None:
    from medomni.studio.build import _arm, config_hashes
    from medomni.studio.build.recipes import check_package

    packages: set = set()
    staged: dict[str, set[str]] = {}
    expected_by_dataset: dict[str, set[str]] = {}
    from medomni.core import plugins

    arms = plugins.resolve(plugins.ARMS).pieces
    if scope.pairs:
        _vectors(sink)
    for pair_id in scope.pairs:
        pair = common.load_pair(pair_id)
        metrics = {t.metric for t in pair.template.targets}
        known = set(plugins.resolve(plugins.METRICS).pieces)
        sink.add("T-COMP.1", "M", pair_id, PASS if metrics <= known else FAIL, f"metrics {sorted(metrics)}", "template")
        sink.add("T-CONF.4", "M", pair_id, PASS if metrics <= known else FAIL, "metrics registered in medomni.metrics", "template")
        if pair.package not in packages:
            packages.add(pair.package)
            problems = check_package(pair.package)
            sink.add("T-CONF.1", "M", pair.dataset, FAIL if problems else PASS, "; ".join(problems)[:400] or "the package's checks across files pass", "studio.build.recipes")
        meta = common.content(scope.ws, pair_id)
        if meta is None:
            sink.add("T-COMP.2", "M", pair_id, NONE, "not built", "content")
            continue
        atoms = common.built_atoms(scope.ws, pair_id, meta)
        _bench_results(scope, sink, pair_id)
        _atom_gates(scope, sink, pair_id, atoms, meta)
        man = common.manifest(scope.ws, pair_id)
        if man is None:
            sink.add("T-COMP.3", "M", pair_id, FAIL, "no build manifest", "manifest.json")
            continue
        sink.add("T-COMP.3", "M", pair_id, PASS, f"{len(man['config_hash'])} arm config hashes recorded", "manifest.json")
        staged[pair.dataset] = staged.get(pair.dataset, set()) | _staged_families(atoms)
        expected_by_dataset[pair.dataset] = declared_families(pair.package)
        keys = {arm.split("/")[0] for arm in man["config_hash"]}
        expected = config_hashes(pair, [_arm(k) for k in sorted(keys) if k in arms])
        same = {k: man["config_hash"].get(k) == v for k, v in expected.items()}
        ok = all(same.values()) and len(same) == len(man["config_hash"])
        sink.add("T-CONF.2", "M", pair_id, PASS if ok else FAIL,
                 "recomputed config hashes match the manifest" if ok else f"config hash differs from the manifest for {[k for k, v in same.items() if not v]}", "config_hash")
    _supply(sink, staged, expected_by_dataset)
