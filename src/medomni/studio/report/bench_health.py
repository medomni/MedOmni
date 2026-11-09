"""`medomni studio bench-health <run>`: each encoder's health from a finished run's call logs (the sidecar's
`verifier/gateway_usage.json` per trial). Aggregates only: no subject, atom or path in the output.

    PASS           every call healthy or a card-declared refusal, and at least one healthy
    DECLARED-ONLY  no healthy call, only declared refusals
    FAIL           any undeclared failure
    NO-EVIDENCE    the encoder was never called
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from .. import common
from ..tools import Report, Result


def outcome(c: dict) -> str:
    if c.get("refused"):
        return "refused"  # the sidecar's budget or breaker, not the encoder
    if c.get("outcome") == "healthy":
        return "healthy"
    if c.get("outcome") == "declared" or c.get("not_applicable"):
        return "declared"
    if c.get("outcome") == "bad_request":
        return "bad_request"  # the caller's fault, never the encoder's
    return "undeclared"


def verdict(n: Counter) -> str:
    if n["undeclared"]:
        return "FAIL"
    if n["healthy"]:
        return "PASS"
    if n["declared"]:
        return "DECLARED-ONLY"
    return "NO-EVIDENCE"


def collect(run: Path) -> dict:
    agg: dict = defaultdict(Counter)
    for g in run.glob("**/verifier/gateway_usage.json"):
        dataset = g.parents[1].name.split("_")[0]
        for c in json.loads(g.read_text(encoding="utf-8")).get("calls") or []:
            agg[(c.get("encoder_id") or "?", dataset)][outcome(c)] += 1
    return agg


class BenchHealth(Report):
    name = "bench-health"
    summary = "report each encoder's health from a finished run's call log"
    target = "run"
    target_help = "a run under the workspace's runs folder"

    def make(self, target, a, ctx) -> Result:
        run = common.run_dir(ctx.ws, target)
        agg = collect(run)
        if not agg:
            return Result(f"{target}: no call logs (verifier/gateway_usage.json) in this run", code=1)
        rows = [[verdict(n), ds, e, dict(sorted(n.items()))] for (e, ds), n in sorted(agg.items(), key=lambda kv: (kv[0][1], kv[0][0]))]
        doc = [{"verdict": v, "dataset": d, "encoder": e, "counts": c, "run": target} for v, d, e, c in rows]
        text = common.table(["verdict", "dataset", "encoder", "counts"], rows)
        return Result(text, {f"{target}.yaml": yaml.safe_dump({"results": doc}, sort_keys=False)})
