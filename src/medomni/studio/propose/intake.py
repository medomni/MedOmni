"""`medomni studio intake`: proposal rows to drafts, and a signed-off proposal to a template (v0.2's `intake/` and
`task_template_builder/`).

    medomni studio intake proposals.csv         # one draft proposal and one catalogue page per row, plus MANIFEST.md
    medomni studio intake <proposal>.yaml       # a signed-off proposal to <template>/template.yaml and its cohorts

A draft carries an `unresolved` list; a proposal freezes only once it is `signed-off` and nothing stays unresolved.
Output goes to the workspace; the frozen template is opened as a pull request to Bench by a person.
"""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

import yaml

from .. import common
from ..tools import Propose, Result, ToolError

# v0.2's proposal forms name datasets by their v0.2 names (R-68); a column has several spellings across its exports
DATASETS = {"mimic": "mimic-iv"}
COLUMNS = {"received_at": "at", "timestamp": "at", "name": "by", "proposer": "by", "institution": "org", "org": "org",
           "dataset": "dataset", "task_name": "title", "title": "title", "statement": "statement", "mode": "mode",
           "targets": "targets", "target": "targets", "streams": "streams", "prediction_time": "prediction_time"}
DROP = {"and", "predict", "prediction", "of", "the", "a", "an", "using", "early", "recognition", "status", "related",
        "parameters", "derived", "data"}
ABBREV = {"coagulation": "coag", "disorders": "", "disorder": "", "heart": "hf", "failure": "", "cardiac": "hf",
          "peripheral": "", "diabetic": "dpn", "polysomnography": "psg", "physiology": "", "overnight": "sleep",
          "complication": "", "phenotype": "", "infarction": "infarct", "cerebral": "stroke", "septicemia": "sepsis",
          "depressive": "depression", "severity": "", "symptom": ""}


def propose_id(title: str, dataset: str, taken: set[str] | None = None) -> str:
    """A template id `<dataset>_<slug>` from a proposal title: load-bearing words, at most 4 words / 28 characters."""
    parts = re.split(r"\b(?:from|at|using)\b", title.lower(), maxsplit=1)
    head, tail = parts[0], (parts[1] if len(parts) > 1 else "")
    words: list[str] = []
    for w in re.findall(r"[a-z0-9]+", head):
        w = ABBREV.get(w, w) if w not in DROP else ""
        if w and w not in words:
            words.append(w)
    more = [ABBREV.get(w, w) for w in re.findall(r"[a-z0-9]+", tail) if w not in DROP and ABBREV.get(w, w)]
    if more and len(words) < 3:
        words.append(more[0])
    slug = "-".join(words[:4])[:28].rstrip("-") or "task"
    tid = base = f"{dataset}_{slug}"
    if taken is not None:
        k = 2
        while tid in taken:
            tid, k = f"{base}-{k}", k + 1
        taken.add(tid)
    return tid


def read_rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if rows and not ({"statement"} <= {COLUMNS.get(k, k) for k in rows[0]}):
        raise ToolError(f"{path} has no statement column; it is not a proposals export")
    out = []
    for row in rows:
        r = {COLUMNS.get((k or "").strip(), k): (v or "").strip() for k, v in row.items() if k}
        if r.get("title") or r.get("statement"):
            r["dataset"] = DATASETS.get(r.get("dataset", ""), r.get("dataset", ""))
            out.append(r)
    return out


def chips(cell: str) -> list[str]:
    return [p.strip() for p in (cell or "").split("|") if p.strip()]


def fingerprint(r: dict) -> str:
    """Changes when the proposal changes, so a changed row is visible and an unchanged one is byte-stable."""
    norm = "\n".join([r.get("dataset", ""), r.get("title", ""), r.get("statement", ""), r.get("mode", ""),
                      *chips(r.get("targets", "")), *chips(r.get("streams", ""))])
    return hashlib.sha256(norm.encode()).hexdigest()[:16]


def draft(r: dict, tid: str) -> dict:
    unresolved = ["targets name no label yet: write label references", "no cohort written yet"]
    if not r.get("prediction_time"):
        unresolved.append("prediction time missing: it is the leakage boundary")
    return {"title": r.get("title") or tid, "by": r.get("by") or "unknown", "org": r.get("org") or None,
            "at": r.get("at") or "unknown", "mode": r.get("mode") or "unknown", "state": "draft",
            "dataset": r.get("dataset") or None,
            "draft": {"template_id": tid, "statement": r.get("statement", ""), "targets": chips(r.get("targets", "")),
                      "streams": chips(r.get("streams", "")), "prediction_time_note": r.get("prediction_time") or None,
                      "fingerprint": fingerprint(r), "unresolved": unresolved}}


PAGE = """# {title}

| Field | Value |
|---|---|
| Template ID | `{tid}` |
| Dataset | {dataset} |
| Mode | {mode} |
| Proposer | {by} ({org}) |
| Received | {at} |
| Fingerprint | `{fingerprint}` |

## Statement

{statement}

## Targets

{targets}

## Streams

{streams}
"""


def page(p: dict) -> str:
    d = p["draft"]
    return PAGE.format(title=p["title"], tid=d["template_id"], dataset=p["dataset"], mode=p["mode"], by=p["by"],
                       org=p["org"] or "?", at=p["at"], fingerprint=d["fingerprint"],
                       statement=d["statement"] or "(no statement given)",
                       targets="\n".join(f"- {t}" for t in d["targets"]) or "- (none listed)",
                       streams="\n".join(f"- {s}" for s in d["streams"]) or "- (none listed)")


class Intake(Propose):
    name = "intake"
    summary = "turn proposal rows into drafts, or a signed-off proposal into a template"
    target = "file"
    target_help = "a proposals .csv, or a proposal .yaml to freeze"

    def make(self, target, a, ctx) -> Result:
        path = Path(target)
        if not path.is_file():
            raise ToolError(f"no such file: {path}")
        return self._freeze(path) if path.suffix in (".yaml", ".yml") else self._intake(path)

    def _intake(self, path: Path) -> Result:
        from medomni.core.contracts import TaskProposal, load_data

        taken: set[str] = set()
        files, rows = {}, []
        for r in read_rows(path):
            tid = propose_id(r.get("title", ""), r.get("dataset") or "unknown", taken)
            p = draft(r, tid)
            load_data(p, TaskProposal, f"proposal {tid}")  # refuse now, not in review
            files[f"{tid}.yaml"] = yaml.safe_dump(p, sort_keys=False, allow_unicode=True, width=1000)
            files[f"{tid}.md"] = page(p)
            rows.append([f"`{tid}`", p["dataset"], p["at"], len(p["draft"]["targets"]), len(p["draft"]["streams"]),
                         len(p["draft"]["unresolved"]), f"`{p['draft']['fingerprint']}`"])
        text = common.table(["template", "dataset", "received", "targets", "streams", "unresolved", "fingerprint"], rows)
        files["MANIFEST.md"] = f"# Task proposals\n\nWritten from `{path.name}`.\n\n{text}\n"
        return Result(f"{len(rows)} draft proposal(s) from {path.name}", files)

    def _freeze(self, path: Path) -> Result:
        from medomni.core.contracts import Cohort, TaskProposal, TaskTemplate, load, load_data

        p = load(path, TaskProposal)
        if p.state != "signed-off":
            raise ToolError(f"{path.name}: state is {p.state}; only a signed-off proposal is frozen")
        d = dict(p.draft)
        if d.get("unresolved"):
            raise ToolError(f"{path.name}: unresolved items remain: " + "; ".join(map(str, d["unresolved"])))
        for key in ("template", "cohort"):
            if key not in d:
                raise ToolError(f"{path.name}: draft has no {key}: block")
        tpl = load_data(d["template"], TaskTemplate, f"{path.name}: template")
        cohort_name = d.get("cohort_name", "n20")
        load_data(d["cohort"], Cohort, f"{path.name}: cohort")
        folder = tpl.template_id
        files = {f"{folder}/template.yaml": yaml.safe_dump(d["template"], sort_keys=False, allow_unicode=True, width=1000),
                 f"{folder}/cohorts/{cohort_name}.yaml": yaml.safe_dump(d["cohort"], sort_keys=False, width=1000)}
        return Result(f"frozen {tpl.template_id}; open it as a pull request to Bench", files)
