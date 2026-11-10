"""Part 3, check 3 (U3.3): Build, fed v0.2's sources and v0.2's draw, gives v0.2's atoms. The only place v0.2's draw lives (R-118).

T4: needs v0.2.1's checkout, the raw copies and a workspace; hours for the whole set. Run one dataset with
`MEDOMNI_REPRO_ONLY=aireadi pytest -m baseline tests/bench/repro`. Prints counts only.
"""
from __future__ import annotations

import collections
import csv
import filecmp
import json
import os
import random
import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.baseline

V02 = Path(os.environ.get("MEDOMNI_V02", "<v0.2 checkout>"))
WORKSPACE = Path(os.environ.get("MEDOMNI_STAGE3_WORKSPACE", "<workspace>/workspace.yaml"))
TREE = Path(os.environ.get("MEDOMNI_REPRO_TASKS", "<workspace>/repro-tasks"))
ATOMS = {"n20": ("atomtasks", "encoders"), "ladder": ("atomtasks-ladder", "modality-ladder")}
DATASET = {"mimic-iv": "mimic", "aireadi": "aireadi", "bdsp": "bdsp"}


def old_name(template: str) -> str:
    return "mimic_" + template[len("mimic-iv_"):] if template.startswith("mimic-iv_") else template


def parent(pair) -> dict:
    tree, _ = ATOMS[pair.cohort_name]
    batch = "r1" if pair.cohort_name == "ladder" else "n20"
    return json.loads((V02 / "data_task" / tree / "_parents" / f"{old_name(pair.template.template_id)}__{batch}/parent.json").read_text())


def v02_source(pair) -> set[str]:
    return {p.stem for p in (V02 / "data_manifest/dataplane" / DATASET[pair.dataset] / "patients").glob("*.json")}


def _split(n, k):
    base, extra = divmod(n, k)
    return [base + (1 if i < extra else 0) for i in range(k)]


def v02_draw(result) -> list[str]:
    """v0.2's seeded shuffle (emit_atomic.draw_cohort, ladder.cohort), over the same pool. BDSP's drawn nights come from
    v0.2 (R-37): a night that fails conversion leaves the pool, so a shuffle over it can't return v0.2's cohort."""
    pair = result.pair
    if pair.dataset == "bdsp":
        return [s for s in parent(pair)["cohort"] if s in result.patients]
    primary = pair.template.targets[0].name
    n, seed = pair.cohort.select.n, pair.cohort.select.seed
    gold = {s: int(p.answers[primary]) for s, p in result.patients.items() if p.answers[primary] is not None}
    classes = sorted(set(gold.values()))
    if pair.cohort_name == "ladder":
        if pair.dataset == "mimic-iv":  # v0.2's ladder pool knew a chest film by its day only: a same-day film counts as late
            from medomni.studio.build.evidence import before_or_at, boundary

            def early(p):
                return any(e["code"] == "FILE//cxr-radiograph-2d" and before_or_at(str(e["time"])[:10], boundary(p.ctx)) for e in p.ctx.events)

            gold = {s: v for s, v in gold.items() if early(result.patients[s])}
            classes = sorted(set(gold.values()))
        rng, out = random.Random(seed), []
        for c in classes:
            members = sorted(s for s, v in gold.items() if v == c)
            rng.shuffle(members)
            out += members[: n // len(classes)]
        return out
    rng, out = random.Random(seed), []
    if pair.cohort.select.balance:
        film = {s: bool(p.balance[pair.cohort.select.balance[0]]) for s, p in result.patients.items()}
        for c in classes:
            for has in (True, False):
                cell = sorted(s for s in result.patients if gold.get(s) == c and film[s] == has)
                rng.shuffle(cell)
                out += cell[: max(1, n // (2 * len(classes)))]
        return out
    for c, k in zip(classes, _split(n, len(classes))):
        pool = sorted(s for s, v in gold.items() if v == c)
        rng.shuffle(pool)
        out += pool[:k]
    return out


_HEADER = re.compile(rb"Startdate \S+ ")


def same_but_start(new: bytes, old: bytes) -> tuple[bool, bool]:
    """(identical, equal except the start date and time), as check 4's bridge comparison."""
    if new == old:
        return True, True
    if len(new) != len(old):
        return False, False
    n = int(new[252:256])
    hdr = 256 * (n + 1)
    rec_new, rec_old = _HEADER.sub(b"", new[88:168]).rstrip(), _HEADER.sub(b"", old[88:168]).rstrip()
    return False, new[:88] == old[:88] and new[184:hdr] == old[184:hdr] and new[hdr:] == old[hdr:] and rec_new == rec_old


# ---- comparing one atom
def _text(p: Path) -> str:
    return p.read_text(errors="replace")


def _norm_compose(s: str, name: str, raw: dict[str, str]) -> str:
    s = "\n".join(line for line in s.splitlines() if not line.startswith("#"))
    for root in raw.values():
        s = s.replace(root, "<raw>")
    return s.replace(f"medomni-task-{old_name(name)}", "T").replace(f"medomni-task-{name}", "T")


def _rel(s: str, raw: dict[str, str]) -> str:
    for root in raw.values():
        s = s.replace(root, "<raw>")
    return s


def compare(a: Path, b: Path, template: str, raw: dict[str, str], tally, why) -> None:
    names = lambda r: {str(p.relative_to(r)) for p in r.rglob("*") if p.is_file()}  # noqa: E731
    for rel in sorted(names(a) | names(b)):
        key = re.sub(r"\d{4,}", "<n>", rel)
        key = re.sub(r"refs/[^/]+/.*", "refs/*", key)
        key = re.sub(r"files/<n>/.*", "files/*", key)
        if rel in ("data/encoder_manifest.md", "task.toml", "FINGERPRINT", "README.md"):  # R-16; stand-ins; v0.2 only
            continue
        x, y = a / rel, b / rel
        if not y.exists() and rel.endswith("bridge.manifest.jsonl") and not json.loads(_text(x))["families"]:
            continue  # an all-masked rung: v0.2 wrote an empty request
        if not x.exists() or not y.exists():
            why[("only one side", key)] += 1
            tally["differ"] += 1
            continue
        if rel == "data/inventory.json":
            same = {k: v for k, v in json.loads(_text(x)).items() if k != "encoders"} == {k: v for k, v in json.loads(_text(y)).items() if k != "encoders"}
        elif rel == "instruction.md":
            cut = lambda s: s.split("\n", 1)[1]  # noqa: E731
            same = cut(_text(x)) == cut(_text(y))
        elif rel.endswith("docker-compose.yaml"):
            same = _norm_compose(_text(x), template, raw) == _norm_compose(_text(y), template, raw)
        elif rel.endswith("refs.map.json"):
            same = _rel(_text(x), raw) == _rel(_text(y), raw)
        elif rel.endswith("bridge.manifest.jsonl"):  # `skipped` is v0.2's note on families it did not request
            same = {k: v for k, v in json.loads(_rel(_text(x), raw)).items() if k != "skipped"} == json.loads(_rel(_text(y), raw))
        elif rel.endswith(".edf"):  # 27 old nights carry their write time as start time (R-110)
            same = same_but_start(y.read_bytes(), x.read_bytes())[1]
        else:
            same = filecmp.cmp(x, y, shallow=False)
        tally["same" if same else "differ"] += 1
        if not same:
            why[("differ", key)] += 1


def _num(v: str):
    try:
        return float(v)
    except ValueError:
        return v


def gold_rows(old: Path, new: Path, name_of=lambda x: x) -> tuple[int, int]:
    a = {(r["subject_id"], r["target"]): _num(r["value"]) for r in csv.DictReader(open(old))}
    b = {(r["subject_id"], r["target"]): _num(r["value"]) for r in csv.DictReader(open(new))}
    return sum(a.get(k) == v for k, v in b.items()), len(a)


def _pairs(only):
    from medomni.core import plugins
    from medomni.core.contracts import TaskTemplate, load

    out = {"n20": [], "ladder": []}
    for tpl in sorted((plugins.find_repo() / "studio/datasets").glob("*/tasks/*/template.yaml")):
        t = load(tpl, TaskTemplate)
        if t.dataset not in DATASET or (only and t.dataset != only):  # a dataset new in v0.3 has nothing to compare with
            continue
        for co in ("n20", "ladder"):
            if (tpl.parent / "cohorts" / f"{co}.yaml").is_file():
                out[co].append(f"{t.template_id}@{co}")
    return out


@pytest.fixture(scope="module")
def ws():
    if not V02.is_dir() or not WORKSPACE.is_file():
        pytest.skip("needs v0.2.1's checkout and a workspace")
    from medomni.core import workspace

    return workspace.load(WORKSPACE).model_copy(update={"tasks": str(TREE)})


@pytest.mark.parametrize("cohort", ["n20", "ladder"])
def test_build_reproduces_v02(cohort, ws):
    from medomni.studio.build import build
    from medomni.core import workspace

    only = os.environ.get("MEDOMNI_REPRO_ONLY")
    pairs = _pairs(only)[cohort]
    tree_old, arm = ATOMS[cohort]
    build(pairs, [arm], ws=ws, source_with=v02_source, draw_with=v02_draw, reproduction=True)
    raw = {d: str(workspace.dataset_path(ws, d)) for d in ws.datasets}
    tally, why, cohorts, gold, pools = (collections.Counter() for _ in range(5))
    old_root, new_root = V02 / "data_task" / tree_old, TREE / "atomtasks" / arm
    for pid in pairs:
        template, _, _ = pid.partition("@")
        rungs = ("r1", "r2", "r3", "r4", "r5", "r6") if cohort == "ladder" else (None,)
        for rung in rungs:
            batch = rung or "n20"
            j = json.loads((old_root / "_parents" / f"{old_name(template)}__{batch}/parent.json").read_text())
            atoms = json.loads((TREE / "atomtasks/_content" / pid / "content.json").read_text())["atoms"]
            new_ids = [a["subject"] for a in atoms]
            cohorts["match" if sorted(new_ids) == sorted(j["cohort"]) else "differ"] += 1
            stats = json.loads((TREE / "atomtasks/_content" / pid / "content.json").read_text())["pool_stats"]
            if cohort == "n20":  # v0.2 counted a secondary target's pool before the main target was required: main target only
                t = j["targets"][0]["name"]
                old_counts = {float(k): v for k, v in j["pool_stats"][t]["counts"].items()}
                pools["same" if t in stats and {float(k): v for k, v in stats[t]["counts"].items()} == old_counts else "differ"] += 1
            for s in new_ids:
                a = old_root / f"{old_name(template)}__{s}__{batch}"
                b = new_root / (rung or "") / f"{template}__{s}__{cohort}"
                if a.is_dir():
                    compare(a, b, template, raw, tally, why)
            if rung in (None, "r1"):
                g = gold_rows(old_root / "_parents" / f"{old_name(template)}__{batch}/gold.csv",
                              TREE / "atomtasks/_content" / pid / "answers.csv")
                gold["same"] += g[0]
                gold["total"] += g[1]
    print(dict(tally), dict(cohorts), dict(gold), "pool stats", dict(pools))
    for k, v in sorted(why.items()):
        print(k, v)
    assert not why and not cohorts.get("differ") and gold["same"] == gold["total"] and not pools.get("differ")
