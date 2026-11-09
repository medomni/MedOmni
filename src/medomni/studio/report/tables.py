"""`medomni studio tables [--set <set>]`: the results table: task × (intelligence × arm), from the results file
(v0.2's `analyze.py grid`; the legacy exp_type reductions are not rebuilt). Reads the record contracts only."""
from __future__ import annotations

import json

from .. import common
from ..tools import Report, Result


class Tables(Report):
    name = "tables"
    summary = "write the results table of the scored runs"

    def options(self, p) -> None:
        p.add_argument("--set", dest="set_name", help="only this task set (<benchmark>/<set>)")

    def make(self, target, a, ctx) -> Result:
        runs, scores = common.results(ctx.ws)
        if a.set_name:
            scores = [s for s in scores if s.task_set == a.set_name]
            runs = [r for r in runs if r.task_set == a.set_name]
        if not scores:
            return Result(f"no scored runs{' for ' + a.set_name if a.set_name else ''} in {ctx.ws.results}", code=1)
        attempts: dict = {}
        for r in runs:
            arm = r.agent.arm if r.agent else None
            variant = r.agent.arm_variant if r.agent else None
            c = attempts.setdefault((r.task, r.intelligence.name, arm, variant), [0, 0, 0.0])
            c[0] += 1
            c[1] += bool(r.error_kind)
            c[2] += r.api_cost or 0
        cols = sorted({(s.intelligence.name, s.arm, s.arm_variant) for s in scores}, key=lambda x: (x[0], str(x[1]), str(x[2])))
        by = {(s.target, s.intelligence.name, s.arm, s.arm_variant): s for s in scores}
        tasks = sorted({s.target for s in scores})
        head = [f"{i} · {arm or '-'}{f'/{v}' if v else ''}" for i, arm, v in cols]
        rows, data = [], {}
        for t in tasks:
            row = [t]
            for i, arm, v in cols:
                s = by.get((t, i, arm, v))
                if s is None:
                    row.append("—")
                    continue
                task = next((r.task for r in runs if r.run_id == s.run_id), None)
                n_att, n_err, cost = attempts.get((task, i, arm, v), (0, 0, 0.0))
                value = "no value" if s.value is None else f"{s.value:.3f}"
                row.append(f"{value} ({s.n_atoms}, {100 * n_err / max(n_att, 1):.0f} %, ${cost / max(n_att, 1):.3f})")
                data[f"{t}::{i}::{arm}::{v}"] = {"value": s.value, "n_atoms": s.n_atoms, "n_failed": s.n_failed, "flags": list(s.flags)}
            rows.append(row)
        text = "Cell: value (n, err %, $/attempt).\n\n" + common.table(["target", *head], rows)
        return Result(text, {"results.md": text + "\n", "results.json": json.dumps(data, indent=1) + "\n"})
