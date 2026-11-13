"""`medomni studio review-form <template>@<cohort>`: a task's review form, bound to its config hash (R-114).

The form is a YAML file a reviewer fills in; `--submit <form>` records it as a human verdict line, which is what the
audit reads. A form whose hash no longer matches the task is refused, so a sign-off can't land on a changed task.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from .. import common
from ..tools import Result, Review, ToolError
from . import matrix, verdicts
from .audit import reviews_dir


class ReviewForm(Review):
    name = "review-form"
    summary = "write a task's clinical review form, or record a filled-in one"
    target = "pair"
    target_help = "<template>@<cohort>"

    def options(self, p) -> None:
        p.add_argument("--submit", type=Path, help="a filled-in form to record as this task's human verdicts")

    def make(self, target, a, ctx) -> Result:
        pair = common.load_pair(target)
        bound = verdicts.task_binding(pair)
        if a.submit:
            return self._submit(target, bound, a.submit)
        cells = matrix.cells()
        checks = {k: {"text": t, "outcome": "", "note": ""} for k, t in cells["T-CLIN"]["checks"].items()}
        form = {"task": target, "hash": bound, "signed_by": "", "date": "", "checks": checks,
                "statement": pair.template.agent.statement,
                "targets": [{"name": t.name, "label": t.label, "metric": t.metric, "question": t.question} for t in pair.template.targets]}
        slug = target.replace("@", "_").replace(":", "_")
        return Result(f"{target}: bound to {bound}", {f"{slug}.yaml": yaml.safe_dump(form, sort_keys=False, allow_unicode=True, width=1000)})

    def _submit(self, target: str, bound: str, path: Path) -> Result:
        form = yaml.safe_load(path.read_text(encoding="utf-8"))
        if form.get("task") != target:
            raise ToolError(f"{path.name} is the form of {form.get('task')}, not {target}")
        if form.get("hash") != bound:
            raise ToolError(f"{path.name} is bound to {form.get('hash')}, the task is now {bound}: write a new form")
        if not form.get("signed_by"):
            raise ToolError(f"{path.name} is not signed (signed_by)")
        lines = [json.dumps({"check": k, "instance": target, "hash": bound, "outcome": v["outcome"], "note": v.get("note", ""),
                             "by": form["signed_by"], "signed_by": form["signed_by"]})
                 for k, v in form["checks"].items() if v.get("outcome")]
        if not lines:
            raise ToolError(f"{path.name} has no outcome filled in")
        folder = reviews_dir() / "human"
        folder.mkdir(parents=True, exist_ok=True)
        with open(folder / f"{target.replace('@', '_')}.jsonl", "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return Result(f"{target}: recorded {len(lines)} human verdict(s)")
