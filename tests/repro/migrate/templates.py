"""v0.2 task specs -> v0.3 task templates and cohorts (R-68), written into each dataset package's `tasks/`.

    studio/datasets/<dataset>/tasks/<template_id>/template.yaml
    studio/datasets/<dataset>/tasks/<template_id>/cohorts/{n20,ladder}.yaml

Sources (v0.2's from the v0.2.1 tree, `v02`; the fixtures and S1's recipes from this repository):

- the 30 base specs in `data_task/taskbuilder/specs/`; a `-full` twin adds the `full` evidence variant (R-34, R-109)
  and, when it overrides them, the variant's own `input` and `exclude` (`full:`); a `-mini` twin is the n20 tier;
- the targets v0.2 adds in code, `CENSUS_RULED` in `emit_atomic.py` (read as a literal, not imported);
- the cohorts S2 ported from S1's recipes, `tests/core/fixtures/recipes/<dataset>/cohorts.yaml` (n20 and ladder;
  the base `standard` tier was never built and is not converted, Bosong 2026-11-09). The one cohort S2 left out,
  `mimic_icu-stay-radiology@n20`, comes from S1's `p16_recipes.yaml`: its inline balance rule becomes the label
  `derived:cxr-before-anchor`, named by the cohort's `select.balance` so it is never scored (Bosong, 2026-11-09).

`agent.instruction` holds the template's own instruction paragraph: v0.2's definitions block for the kind of prediction
time the template asks about (`templates/blocks/definitions.<kind>.md`).

Field placement (U2.9, Bosong 2026-11-09): `statement` goes into `agent:`; `data_mode` is a dataset rule in
AI-READI's `evidence.yaml`; `version`, `prediction_time_note`, `readme_note`, `approved_by` and
`stream_provenance` are dropped (the cohort's N.X replaces `version`; sign-off is Studio review, part 6). `seed`,
`cohort` and `prediction_time` live in the cohort files. `environment.bundle` has no v0.3 field.

MIMIC's dataset id is `mimic-iv`, so its templates are renamed `mimic_<name>` -> `mimic-iv_<name>` (R-94);
`NAME_MAP` is read by part 3's check 3 and part 5's record import.
"""
from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import yaml

from . import V02_COMMIT
from .cards import git_authors

SPECS = "data_task/taskbuilder/specs"
EMIT = "data_task/taskbuilder/emit_atomic.py"
BLOCKS = "data_task/taskbuilder/templates/blocks"
LADDER = "data_task/taskbuilder/ladder.yaml"
ICD_CODE = "^DIAGNOSIS//ICD//({})"
FIXTURES = "tests/core/fixtures/recipes"
S1_RECIPES = "internal_docs/roadmaps/v0.3.0/roadmaps/probes/s1/p16_recipes.yaml"
DEST = "studio/datasets"
TIERS = ("n20", "ladder")
COHORT_VERSION = "1.0"  # R-106
HEADER = "# Converted from v0.2.1's task specs by `python -m medomni.core.contracts.convert templates` (R-68).\n"  # as written in Stage 3 part 2

DATASETS = {"mimic": "mimic-iv", "aireadi": "aireadi", "bdsp": "bdsp"}  # v0.2 dataset -> package
NAME_MAP = {  # v0.2 template id -> v0.3 template id (R-94)
    "mimic_acute-renal-hospital": "mimic-iv_acute-renal-hospital",
    "mimic_ckd-staging": "mimic-iv_ckd-staging",
    "mimic_coag-hemorrhagic": "mimic-iv_coag-hemorrhagic",
    "mimic_heart-failure-mm": "mimic-iv_heart-failure-mm",
    "mimic_hf": "mimic-iv_hf",
    "mimic_icu-stay-radiology": "mimic-iv_icu-stay-radiology",
    "mimic_in-hospital-death-icu": "mimic-iv_in-hospital-death-icu",
    "mimic_sepsis-hospital": "mimic-iv_sepsis-hospital",
    "mimic_stroke-infarct-ed": "mimic-iv_stroke-infarct-ed",
}
DROPPED = ("version", "prediction_time_note", "readme_note", "approved_by", "stream_provenance")  # U2.9
ENVIRONMENT = ("cpus", "memory_mb", "allow_internet", "agent_timeout_sec", "verifier_timeout_sec")
AUTHOR_ALIASES = {"Boson": "Bosong Huang"}  # one person, two git names (same GitHub account)

# The one cohort S2 did not port: its inline balance rule, as a label and a target
INLINE = {"mimic_icu-stay-radiology@n20": {
    "rule": {"exists": "CXR//STUDY", "to": "anchor"},
    "label": "derived:cxr-before-anchor",
}}
# v0.2 worded one target by the prediction time: here it is asked at admission, not 24 hours in
QUESTIONS = {"mimic_icu-stay-radiology": {"in_hospital_death": (
    "Your prediction is the probability that the patient dies before discharge from the index admission. "
    "Higher values MUST mean more likely positive/higher class — do not invert.")}}
INLINE_LABELS = {"mimic-iv": {"derived:cxr-before-anchor": {"exists": "CXR//STUDY", "from": "any", "to": "anchor"}}}


def census(repo: Path) -> dict[str, list[tuple[str, str]]]:
    """`CENSUS_RULED` from v0.2's emit_atomic.py: template -> [(target name, derivation)]."""
    tree = ast.parse((repo / EMIT).read_text(encoding="utf-8"))
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else (node.targets[0] if isinstance(node, ast.Assign) else None)
        if isinstance(target, ast.Name) and target.id == "CENSUS_RULED":
            return ast.literal_eval(node.value)
    raise ValueError(f"{EMIT}: no CENSUS_RULED")


def metric(derivation: str) -> str:
    """The metric v0.2 scored a code-added target under (emit_atomic.gold_for)."""
    if derivation.startswith(("omopnum:", "labfirst24:")):
        return "mae"
    if derivation.startswith("psgclass:") or derivation == "aireadi-dmstatus":
        return "qwk"
    return "auc"


def _spec(repo: Path, name: str) -> dict | None:
    p = repo / SPECS / f"{name}.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.is_file() else None


def _fixtures(repo: Path) -> dict[str, dict]:
    out = {}
    for ds in DATASETS:
        p = repo / FIXTURES / ds / "cohorts.yaml"
        out.update(yaml.safe_load(p.read_text(encoding="utf-8")) or {})
    return out


def _inline_cohort(repo: Path, key: str) -> dict:
    """A cohort from S1's recipe file, converted as S2's port did (p11_port_recipes.py), with the inline balance
    rule replaced by its target."""
    r = copy.deepcopy(yaml.safe_load((repo / S1_RECIPES).read_text(encoding="utf-8"))[key])
    inline = INLINE[key]
    ds = r["dataset"]
    targets = {lab["name"]: f"{ds}:{lab['derivation']}" for lab in r["labels"]}
    by = [b for b in r["draw"]["by"] if b != inline["rule"]]
    if any(not isinstance(b, str) for b in by):
        raise ValueError(f"{key}: draw.by still holds an inline rule")
    cohort = {"source": "all" if r["universe"] == "all" else {}, "anchor": r["anchor"], "require": r["require"],
              "select": {"n": r["draw"]["n"], "by": by, "balance": [inline["label"]], "seed": r["draw"]["seed"]}}
    return {"targets": targets, "cohort": cohort}


def _ladder(repo: Path, old_id: str, spec_dataset: str) -> dict | None:
    """The modality-ladder arm's definition for one template (R-89): rungs r1-r6 and the template's masks, as codes."""
    doc = yaml.safe_load((repo / LADDER).read_text(encoding="utf-8"))
    if old_id not in doc["tasks"]:
        return None
    rungs = {f"r{k[1:]}": {f: v for f, v in e.items() if f != "demographics"} for k, e in doc["rungs"][spec_dataset].items()}
    out = {"rungs": rungs}
    pre = (doc.get("masks") or {}).get(old_id, {}).get("icd_prefixes")
    if pre:
        out["masks"] = [ICD_CODE.format("|".join(str(p).replace(".", "") for p in pre))]
    return out


def _definitions(repo: Path, spec: dict) -> str:
    """v0.2's definitions block for the template's kind of prediction time (emit_atomic.boundary_kind)."""
    d = spec["target"]["derivation"]
    if spec["dataset"] == "aireadi":
        kind = "visit"
    elif spec["dataset"] == "bdsp":
        kind = "psg"
    elif "ckd" in d:
        kind = "span"
    elif d == "outcome:icu-admission":
        kind = "adm0"
    else:
        kind = "windowed"
    return (repo / BLOCKS / f"definitions.{kind}.md").read_text(encoding="utf-8").strip()


def _authors(repo: Path, spec: dict, name: str) -> list[dict]:
    by = (spec.get("proposal") or {}).get("by")
    names = [by] if by else git_authors(repo, f"{SPECS}/{name}.yaml", V02_COMMIT)  # R-62
    names = list(dict.fromkeys(AUTHOR_ALIASES.get(n, n) for n in names))
    if not names:
        raise ValueError(f"{name}: no author in the spec or its git history")
    return [{"name": n} for n in names]


def _plain(data):
    """A copy that shares no objects (deepcopy keeps shared references, which YAML writes as aliases)."""
    return json.loads(json.dumps(data))


def _merge(base, over):
    """v0.2's `extends` merge (emit.py `_merge`): deep for mappings, the child wins otherwise."""
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = _merge(base.get(k), v)
        return out
    return over


def _exclude(raw: dict) -> dict[str, list[str]]:
    return {k: [str(x) for x in v] for k, v in raw.items()}


def _label(ds: str, ref: str) -> str:
    """`mimic:derived:x` (S2's fixtures) -> `mimic-iv:derived:x`."""
    old, _, label = ref.partition(":")
    if DATASETS.get(old, old) != ds:
        raise ValueError(f"{ref}: label of another dataset than {ds}")
    return f"{ds}:{label}"


def convert(repo: Path, v02: Path | None = None) -> tuple[dict[str, dict], dict[str, dict]]:
    """{path: data} for every template and cohort, and per-template notes. `v02`: the v0.2.1 tree (default `repo`)."""
    repo = Path(repo)
    v02 = Path(v02 or repo)
    fixtures = _fixtures(repo)
    extra = census(v02)
    outputs, notes = {}, {}
    bases = sorted(p.stem for p in (v02 / SPECS).glob("*.yaml") if not p.stem.endswith(("-full", "-mini")))
    for old_id in bases:
        spec = _spec(v02, old_id)
        if spec["task_id"] != old_id:
            raise ValueError(f"{old_id}.yaml: task_id {spec['task_id']}")
        ds = DATASETS[spec["dataset"]]
        tid = NAME_MAP.get(old_id, old_id)
        if not tid.startswith(f"{ds}_"):
            raise ValueError(f"{old_id}: no v0.3 id under {ds}")
        full = _spec(v02, f"{old_id}-full")

        cohorts = {}
        for tier in TIERS:
            key = f"{old_id}@{tier}"
            if key in fixtures:
                cohorts[tier] = fixtures[key]
            elif key in INLINE:
                cohorts[tier] = _inline_cohort(repo, key)
        if "n20" not in cohorts:
            raise ValueError(f"{old_id}: no n20 cohort")
        labels = {}  # target name -> label, from every cohort of the template
        for c in cohorts.values():
            for name, ref in c["targets"].items():
                lab = _label(ds, ref)
                if labels.setdefault(name, lab) != lab:
                    raise ValueError(f"{old_id}: target {name} has two labels")

        t = spec["target"]
        ordered = [(t["name"], t["metric"])] + [(n, metric(d)) for n, d in extra.get(old_id, [])]
        ordered += [(n, metric(labels[n].split(":", 1)[1])) for n in sorted(labels) if n not in dict(ordered)]
        targets = []
        for name, m in ordered:
            if name not in labels:
                raise ValueError(f"{old_id}: target {name} has no label in any cohort")
            targets.append({"name": name, "label": labels[name], "metric": m})
            if name in QUESTIONS.get(old_id, {}):
                targets[-1]["question"] = QUESTIONS[old_id][name]

        template = {"template_id": tid, "dataset": ds, "authors": _authors(repo, spec, old_id), "targets": targets,
                    "input": spec["input"]}
        if full is not None:
            if full.get("evidence_mode") != "full" or full.get("extends") != f"{old_id}.yaml":
                raise ValueError(f"{old_id}-full.yaml is not a full twin of {old_id}")
            template["evidence"] = ["default", "full"]
        if spec.get("excluded_from_inputs"):
            template["exclude"] = _exclude(spec["excluded_from_inputs"])
        if full is not None and ("input" in full or "excluded_from_inputs" in full):
            template["full"] = {}
            if "input" in full:  # the twin's merged input, so `full.input` replaces `input` whole
                template["full"]["input"] = _merge(spec["input"], full["input"])
            if "excluded_from_inputs" in full:
                template["full"]["exclude"] = _exclude(_merge(spec.get("excluded_from_inputs") or {},
                                                              full["excluded_from_inputs"]))
        env = spec["environment"]
        template["agent"] = {"statement": spec["statement"], "instruction": _definitions(v02, spec),
                             "environment": {k: env[k] for k in ENVIRONMENT},
                             "submission_path": spec["submission_path"]}

        base = f"{DEST}/{ds}/tasks/{tid}"
        outputs[f"{base}/template.yaml"] = _plain(template)  # no shared objects, so no YAML aliases
        ladder = _ladder(v02, old_id, spec["dataset"])
        if ladder:
            outputs[f"{base}/arms/modality-ladder.yaml"] = _plain(ladder)
        for tier, c in cohorts.items():
            outputs[f"{base}/cohorts/{tier}.yaml"] = _plain({"version": COHORT_VERSION, **c["cohort"]})
        notes[tid] = {"from": old_id, "cohorts": sorted(cohorts), "targets": len(targets),
                      "evidence": template.get("evidence", ["default"]), "full_overrides": sorted(template.get("full", {})),
                      "authors_from": "proposal" if (spec.get("proposal") or {}).get("by") else "git",
                      "dropped": [k for k in DROPPED if k in spec], "data_mode": spec.get("data_mode")}
    return outputs, notes
