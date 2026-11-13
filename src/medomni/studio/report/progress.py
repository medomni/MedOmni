"""`medomni studio progress <run>`: a run's progress, per job: atoms finished of planned, errors, cost, rate and ETA, read
from what the run has written so far. Harbor job folders are read directly (v0.2's layout: one folder per job, one per
trial inside with `result.json`), so the view needs nothing from the harness. Aggregates only."""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
from pathlib import Path

from .. import common
from ..tools import Report, Result


def _stamp(s):
    try:
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def job_stats(job: Path, now: dt.datetime) -> dict:
    trials = [t for t in sorted(job.iterdir()) if t.is_dir()]
    done = err = 0
    cost = 0.0
    ends = []
    for t in trials:
        r = t / "result.json"
        if not r.exists():
            continue
        try:
            d = json.loads(r.read_text(encoding="utf-8"))
        except ValueError:  # a half-written result is a running trial
            continue
        if not d.get("finished_at"):
            continue
        done += 1
        err += bool(d.get("exception_info"))
        e = _stamp(d["finished_at"])
        if e:
            ends.append(e.astimezone(dt.timezone.utc) if e.tzinfo else e.replace(tzinfo=dt.timezone.utc))
        tj = t / "agent/trajectory.json"
        if tj.exists():
            try:
                cost += (json.loads(tj.read_text(encoding="utf-8")).get("final_metrics") or {}).get("total_cost_usd") or 0
            except ValueError:
                pass
    recent = [e for e in ends if (now - e).total_seconds() < 900]
    rate = len(recent) / 15 if recent else 0.0  # finished atoms per minute over the last 15 minutes
    planned = _planned(job) or len(trials)  # a job's dataset, if its config names one; else the folders so far
    return {"planned": planned, "done": done, "err": err, "cost": cost, "rate": rate,
            "eta_min": (planned - done) / rate if rate and planned > done else None}


def _planned(job: Path) -> int:
    cfg = job / "config.json"
    if not cfg.is_file():
        return 0
    try:
        datasets = json.loads(cfg.read_text(encoding="utf-8")).get("datasets") or []
    except ValueError:
        return 0
    return sum(sum(1 for _ in Path(d["path"]).iterdir()) for d in datasets if d.get("path") and Path(d["path"]).is_dir())


def bar(done: int, planned: int, width: int = 24) -> str:
    f = int(width * done / planned) if planned else 0
    return "#" * f + "." * (width - f)


class Progress(Report):
    name = "progress"
    summary = "show a run's progress: per job, finished of planned, errors, cost, rate, ETA"
    target = "run"
    target_help = "a run under the workspace's runs folder"

    def make(self, target, a, ctx) -> Result:
        run = common.run_dir(ctx.ws, target)
        jobs = sorted(p for p in run.iterdir() if p.is_dir() and any(c.is_dir() for c in p.iterdir())) or [run]
        now = dt.datetime.now(dt.timezone.utc)
        lines = []
        total = [0, 0, 0.0]
        for j in jobs:
            s = job_stats(j, now)
            total[0] += s["done"]; total[1] += s["planned"]; total[2] += s["cost"]
            eta = f"{s['eta_min'] / 60:4.1f} h" if s["eta_min"] else "  —  "
            lines.append(f"{j.name:34s} {bar(s['done'], s['planned'])} {s['done']:4d}/{s['planned']:<4d} "
                         f"err {s['err']:3d}  ${s['cost']:7.2f}  {s['rate']:4.1f}/min  ETA {eta}")
        la = os.getloadavg()
        free = shutil.disk_usage(run).free / 2**30
        lines.append(f"TOTAL {total[0]}/{total[1]} atoms · ${total[2]:.2f} · load {la[0]:.1f}/{la[1]:.1f} · free {free:.0f} GB")
        return Result("\n".join(lines))
