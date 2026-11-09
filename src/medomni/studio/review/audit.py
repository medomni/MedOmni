"""`medomni studio audit`: one engine over five assets. Machine checks run on every audit and can only reject; LLM and
human verdicts are read from the workspace; an item fails only if it harms the main claim (see `engine.py`).

Writes REPORT.md, FINDINGS.md, matrix.json, bindings.json (what a verdict must carry) and records/<asset>.jsonl.
"""
from __future__ import annotations

import importlib
import json
from collections import defaultdict
from pathlib import Path

from medomni.core import workspace

from .. import common
from ..tools import Result, Review
from . import engine, matrix, verdicts
from .matrix import FAIL, NONE, PASS, WARN
from .scope import Scope

STATUS = {PASS: "Pass", WARN: "Warning", FAIL: "Failure", NONE: "Unassessed"}
NOTES = ("Machine checks only reject: Pass means no contradiction was found, not that the asset is sound.",
         "R-ISOL's LLM half is unassessed: judging it needs agent trace content, which the DUA keeps from a hosted model.")


def reviews_dir() -> Path:
    return workspace.home() / "studio" / "review" / "audit" / "reviews"


def _pct(r) -> str:
    return "—" if r is None else f"{100 * r:.1f}%"


def _cell_str(v: dict) -> str:
    t, ass = v["tally"], [o["outcome"] for o in v["checks"].values() if o["outcome"] != NONE]
    ok = sum(o == PASS for o in ass)
    return (f"{STATUS[v['outcome']]} · items {_pct(t['rate'])} ({t['pass']}/{t['assessed']}) · checks {ok}/{len(ass)} of {len(v['checks'])}"
            if t["assessed"] else f"{STATUS[v['outcome']]} · checks 0/0 of {len(v['checks'])}")


def render(cells: dict, items: list, scope, agg: dict) -> str:
    all_t = engine.tally(items)
    by_aud = {a: engine.tally([i for i in items if i.auditor == a]) for a in "MLH"}
    status: dict = defaultdict(int)
    for per in agg.values():
        for v in per.values():
            status[v["outcome"]] += 1
    lines = ["# MedOmni audit", "", "`Pass` = no contradiction found, not soundness. Aggregates only (DUA): atom ids are masked.", "",
             f"**Scope:** {len(scope.datasets)} datasets · {len(scope.families)} families · {len(scope.encoders)} encoders · "
             f"{len(scope.pairs)} built pairs · {len(scope.run_records[0])} runs", "",
             f"**Overall item pass rate {_pct(all_t['rate'])}** ({all_t['pass']} pass · {all_t['warn']} warn · {all_t['fail']} fail of "
             f"{all_t['assessed']} assessed; {all_t['unassessed']} unassessed). Machine {_pct(by_aud['M']['rate'])} · "
             f"LLM {_pct(by_aud['L']['rate'])} · human {_pct(by_aud['H']['rate'])}.", "",
             "**Cells:** " + " · ".join(f"{STATUS[o]} {status[o]}" for o in (PASS, WARN, FAIL, NONE)), "",
             "## The matrix", "", "| Asset | " + " | ".join(matrix.DIMS) + " |", "|---" * (len(matrix.DIMS) + 1) + "|"]
    for asset, prefix in matrix.ASSETS.items():
        row = []
        for code in matrix.DIMS.values():
            cid = f"{prefix}-{code}"
            row.append(f"{cid}<br>" + "<br>".join(f"**{a}** {_cell_str(agg[cid][a])}" for a in cells[cid]["auditors"]))
        lines.append(f"| {asset} | " + " | ".join(row) + " |")
    lines += ["", "## Atomic checks", "", "| Check | Auditor | Outcome | pass / warn / fail / unassessed | Leading finding |",
              "|---|---|---|---|---|"]
    firsts: dict = defaultdict(list)
    for i in items:
        if i.outcome != PASS:
            firsts[(i.check, i.auditor, i.outcome)].append(i)
    for cid, c in cells.items():
        for k, text in c["checks"].items():
            for a in c["auditors"]:
                if k not in agg[cid][a]["checks"]:
                    continue
                v = agg[cid][a]["checks"][k]
                t = v["tally"]
                lead = next((f"{o}: `{firsts[(k, a, o)][0].instance}` — {firsts[(k, a, o)][0].detail}" for o in (FAIL, WARN, NONE) if firsts[(k, a, o)]), "")
                lines.append(f"| **{k}** {text} | {a} | {STATUS[v['outcome']]} | {t['pass']} / {t['warn']} / {t['fail']} / {t['unassessed']} | {lead.replace('|', chr(92) + '|')} |")
    lines += ["", "## Notes", ""] + [f"- {n}" for n in NOTES]
    return "\n".join(lines) + "\n"


def findings(cells: dict, items: list) -> str:
    lines = ["# Findings: every non-pass item", "", "Aggregates and masked ids only.", ""]
    by: dict = defaultdict(list)
    for i in items:
        if i.outcome != PASS:
            by[(i.check, i.auditor)].append(i)
    for c in cells.values():
        for k, text in c["checks"].items():
            for a in c["auditors"]:
                its = by.get((k, a))
                if not its:
                    continue
                grp: dict = defaultdict(list)
                for i in its:
                    grp[(i.outcome, i.detail)].append(i.instance)
                lines += [f"## {k} [{a}] — {len(its)} item(s)", "", f"_{text}_", ""]
                for (o, d), inst in sorted(grp.items(), key=lambda x: x[0][0]):
                    show = ", ".join(f"`{x}`" for x in inst[:6]) + (f" … +{len(inst) - 6}" if len(inst) > 6 else "")
                    lines.append(f"- **{o}** ×{len(inst)} — {d} — {show}")
                lines.append("")
    return "\n".join(lines) + "\n"


def packets(cells: dict, items: list, bound: dict) -> dict[str, str]:
    """One review packet per asset for the LLM auditor: the checks it may assess, the hash its verdict must carry, and
    the machine findings, as masked aggregates (`packets.py` in v0.2). Patient-level traces are never included."""
    by: dict = defaultdict(list)
    for i in items:
        if i.auditor == "M" and i.outcome in (FAIL, WARN):
            by[i.check[0]].append(i)
    out = {}
    for asset, prefix in matrix.ASSETS.items():
        lines = [f"# Review packet: {asset}", "", "Write one JSON line per (check, instance) to `reviews/llm/<any>.jsonl`:",
                 '`{"check", "instance", "hash", "outcome": "pass|warn|fail", "note", "by"}`. `hash` is the instance\'s binding below.', "",
                 "## Checks", ""]
        for cid, c in cells.items():
            if cid.startswith(prefix) and "L" in c["auditors"]:
                lines += [f"- **{k}** {text}" for k, text in c["checks"].items() if (k, "L") not in engine.NOT_FOR and k not in verdicts.LLM_BLOCKED]
        lines += ["", "## Instances and hashes", ""] + [f"- `{k}`: `{v}`" for k, v in sorted(bound.get(prefix, {}).items())]
        lines += ["", "## Machine findings (masked)", ""] + [f"- {i.check} {i.outcome}: `{i.instance}`: {i.detail}" for i in by[prefix]][:200]
        out[f"packets/{asset}.md"] = "\n".join(lines) + "\n"
    return out


def matrix_json(cells: dict, agg: dict) -> dict:
    return {cid: {"asset": cells[cid]["asset"], "dim": cells[cid]["dim"],
                  "auditors": {a: {**v, "checks": {k: {"text": cells[cid]["checks"][k], **cv} for k, cv in v["checks"].items()}}
                               for a, v in per.items()}} for cid, per in agg.items()}


class Audit(Review):
    name = "audit"
    summary = "run the machine checks, read the recorded verdicts, write the report"

    def options(self, p) -> None:
        p.add_argument("--only", help="assets to check, comma-separated: data,families,encoders,tasks,runs")
        p.add_argument("--set", dest="set_name", help="audit one set's pairs (default: every built pair)")
        p.add_argument("--samples", type=Path, help="a folder of family samples to check, one sub-folder per family")

    def make(self, target, a, ctx) -> Result:
        only = [x for x in (a.only or "").split(",") if x] or list(matrix.ASSETS)
        unknown = sorted(set(only) - set(matrix.ASSETS))
        if unknown:
            return Result(f"unknown asset(s) {unknown}; choose from {', '.join(matrix.ASSETS)}", code=2)
        pairs = common.pairs_of(a.set_name) if a.set_name else common.built_pairs(ctx.ws)
        scope = Scope(ctx.ws, pairs, a.samples)
        cells = matrix.cells()
        files, strict = {}, []
        for asset in only:
            sink = engine.Sink(scope.mask)
            importlib.import_module(f"medomni.studio.review.checks.{asset}").run(scope, sink)
            engine.aggregate(cells, sink.items)  # refuse items for a check or auditor the matrix does not assign
            files[f"records/{asset}.jsonl"] = engine.to_jsonl(sink.items)
            strict += sink.items
            t = engine.tally(sink.items)
            print(f"{asset:9s} {len(sink.items):5d} items  pass {t['pass']} warn {t['warn']} fail {t['fail']} unassessed {t['unassessed']}", file=ctx.stream)
        bound = verdicts.bindings(scope)
        items = engine.apply_severity(strict + verdicts.items(reviews_dir(), cells, scope, bound))
        agg = engine.aggregate(cells, items)
        files.update({"REPORT.md": render(cells, items, scope, agg), "FINDINGS.md": findings(cells, items),
                      "matrix.json": json.dumps(matrix_json(cells, agg), indent=1) + "\n",
                      "bindings.json": json.dumps(bound, indent=1, sort_keys=True) + "\n",
                      **packets(cells, items, bound)})
        t = engine.tally(items)
        fails = sum(1 for per in agg.values() for v in per.values() if v["outcome"] == FAIL)
        return Result(f"{len(items)} items, item pass rate {_pct(t['rate'])}, {fails} cell(s) failing", files, 1 if fails else 0)
