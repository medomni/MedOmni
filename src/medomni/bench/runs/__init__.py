"""Run an intelligence on a set's rendered tasks (R-77, R-118). One runner interface: prepare, run, collect."""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Protocol, runtime_checkable

from medomni import __version__
from medomni.core import plugins, workspace
from medomni.core.contracts import AgentConfig, load
from medomni.core.tasks import TaskError, layout
from medomni.core.tasks.checks import task_checks
from medomni.core.tasks.sets import load_set, task_set_hash

RunError = TaskError


def _arm(name: str):
    """An arm's run side, from `medomni.arms`."""
    pieces = plugins.resolve(plugins.ARMS).pieces
    if name not in pieces:
        raise RunError(f"unknown arm '{name}' (registered: {', '.join(sorted(pieces))})")
    return pieces[name].load()


@runtime_checkable
class Runner(Protocol):
    name: str

    def prepare(self, job) -> None: ...

    def run(self, job) -> None: ...

    def collect(self, job) -> None: ...


class Job:
    """One run: an agent on a set under one arm (and variant)."""

    def __init__(self, ws, set_name: str, agent: AgentConfig, arm, variant, rep: int = 1, stamp: str | None = None):
        self.ws, self.set_name, self.agent, self.arm, self.variant, self.rep = ws, set_name, agent, arm, variant, rep
        self.stamp = stamp or dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.task_set, _ = load_set(set_name)
        self.tree = layout.tree(ws)
        condition = f"{arm.name}.{variant}" if variant else arm.name
        self.name = "--".join([set_name.replace("/", "."), agent.name, condition, f"r{rep}", self.stamp])
        self.folder = Path(ws.runs) / self.name

    def atoms(self) -> list[tuple[str, str, Path]]:
        """(pair, atom name, rendered folder) of every atom of the set under this arm."""
        out = []
        for e in self.task_set.tasks:
            meta = json.loads((self.tree / "_content" / e.task / "content.json").read_text(encoding="utf-8"))
            for a in meta["atoms"]:
                d = layout.atom_dir(self.tree, self.arm.name, self.variant, a["atom"])
                if not d.is_dir():
                    raise RunError(f"{a['atom']}: not built under {self.arm.name}; build the set first (`medomni studio task build --set {self.set_name}`)")
                out.append((e.task, a["atom"], d))
        return out


def submission_of(trial: Path) -> dict[str, float] | None:
    p = trial / "verifier/submission.csv"
    try:
        with open(p, newline="", encoding="utf-8") as f:
            return {r["target"]: float(r["prediction"]) for r in csv.DictReader(f)}
    except (OSError, KeyError, ValueError):
        return None


def write_records(job: Job, trials: list[tuple[str, str, Path, str | None, str | None]]) -> None:
    """`runs.jsonl` and `predictions.jsonl` from finished trials: (pair, atom, trial folder, error kind, model served).
    On an arm with the perception service, each trial's encoder calls are counted in its run record and graded into
    `encoder_use.jsonl`, which the scorer summarises."""
    from medomni.bench.scoring import encoder_use
    from medomni.core.contracts import IntelligenceRef, PredictionRecord, RunRecord, load_data

    job.folder.mkdir(parents=True, exist_ok=True)
    hashes, versions = {}, {}
    who = load_data({"kind": "agent", "name": job.agent.name}, IntelligenceRef, "intelligence").model_dump(mode="json")
    key = f"{job.arm.name}/{job.variant}" if job.variant else job.arm.name
    graded = job.arm.max_calls is not None  # only an arm with the perception service has encoder use to grade
    if not graded:
        (job.folder / "encoder_use.jsonl").unlink(missing_ok=True)
    with open(job.folder / "runs.jsonl", "w", encoding="utf-8") as runs, open(job.folder / "predictions.jsonl", "w", encoding="utf-8") as preds, \
            open(job.folder / "encoder_use.jsonl" if graded else os.devnull, "w", encoding="utf-8") as use:
        for pair, atom, trial, error, served in trials:
            content = job.tree / "_content" / pair
            if pair not in hashes:
                hashes[pair] = json.loads((content / "manifest.json").read_text(encoding="utf-8"))["config_hash"][key]
                versions[pair] = json.loads((content / "content.json").read_text(encoding="utf-8"))["version"]
            run_id = f"{job.name}/{atom}"
            doc = {"kind": "run", "run_id": run_id, "release": __version__, "task_set": job.set_name,
                   "task": pair, "task_version": versions[pair], "config_hash": hashes[pair], "intelligence": who,
                   "model_served": served, "error_kind": error, "agent": {"arm": job.arm.name, "arm_variant": job.variant}}
            calls = encoder_use.levels(trial) if graded and (trial / "verifier/gateway_usage.json").is_file() else []
            if calls:
                doc["agent"]["encoder_calls"] = dict(Counter(c["encoder_id"] for c in calls if c["encoder_id"]))
                use.write(json.dumps({"run_id": run_id, "calls": calls}) + "\n")
            runs.write(json.dumps(load_data(doc, RunRecord, run_id).model_dump(mode="json")) + "\n")
            for target, value in (submission_of(trial) or {}).items():
                rec = load_data({"run_id": run_id, "atom": atom, "target": target, "value": value, "intelligence": who}, PredictionRecord, run_id)
                preds.write(json.dumps(rec.model_dump(mode="json")) + "\n")


def counter(done: int, failed: int, total: int, stream=None) -> None:
    """The one-line counter (R-124)."""
    print(f"\r{done}/{total} finished, {failed} failed", end="" if done < total else "\n", file=stream or sys.stdout, flush=True)


class Replay:
    """No model, no Harbor: every target gets a fixed prediction, through the atom's own format check (check 7)."""

    name = "replay"

    def prepare(self, job: Job) -> None:
        job.folder.mkdir(parents=True, exist_ok=True)

    def run(self, job: Job, stream=None) -> None:
        atoms = job.atoms()
        trials, failed = [], 0
        for i, (pair, atom, d) in enumerate(atoms, 1):
            trial = job.folder / atom
            (trial / "verifier").mkdir(parents=True, exist_ok=True)
            targets = json.loads((d / "tests/expected.json").read_text(encoding="utf-8"))["targets"]
            sub = trial / "verifier/submission.csv"
            with open(sub, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["target", "prediction"])
                w.writerows((t, 0.5) for t in targets)
            check = subprocess.run([sys.executable, str(d / "tests/format_check.py"), str(sub), str(d / "tests/expected.json")],
                                   capture_output=True, text=True)
            ok = check.returncode == 0 and json.loads(check.stdout).get("format_ok") == 1
            failed += not ok
            trials.append((pair, atom, trial, None if ok else "agent", "replay"))
            counter(i, failed, len(atoms), stream)
        job.trials = trials

    def collect(self, job: Job) -> None:
        write_records(job, job.trials)


replay = Replay()


def load_agent(name: str) -> AgentConfig:
    agents = plugins.content(plugins.roots(plugins.find_repo())[0])["agents"].pieces
    if name not in agents:
        raise RunError(f"no agent config {name} (found: {', '.join(sorted(agents))})")
    return load(agents[name].path, AgentConfig)


def runner_for(agent: AgentConfig) -> Runner:
    """The runner the agent config names, else the one registered for its kind (R-77, R-145)."""
    pieces = plugins.resolve(plugins.RUNNERS).pieces
    name = agent.runner or agent.kind
    if name not in pieces:
        raise RunError(f"no runner '{name}' (registered: {', '.join(sorted(pieces))})")
    return pieces[name].load()


def preflight(tree: Path, task_set, arms: list[str], route: str | None = None, stream=None) -> None:
    """Before anything runs: Core's checks over built output, on every task of the set under these arms (R-143 a), the
    stand-in agents on each task that passes them (R-54), and the agent's route against each dataset's policy."""
    from medomni.bench.scoring import standins

    from . import routes

    problems = []
    for e in task_set.tasks:
        found = task_checks(tree, e.task, arms)
        problems += found or standins.problems(tree, e.task)
    if route is not None and not problems:
        refused, conditions = routes.check(tree, [e.task for e in task_set.tasks], route)
        problems += refused
        for c in conditions:
            print(f"condition: {c}", file=stream or sys.stdout)
    if problems:
        raise RunError(f"{len(problems)} problem(s) in the built tasks; nothing ran:\n  " + "\n  ".join(problems[:20]))


def run(set_name: str, agent_name: str, arms: list[str] | None = None, ws=None, stream=None) -> list[Path]:
    stream = stream or sys.stdout
    ws = ws or workspace.load()
    agent = load_agent(agent_name)
    task_set, _ = load_set(set_name)
    names = arms or list(task_set.arms)
    bad = sorted(set(names) - set(task_set.arms))
    if bad:
        raise RunError(f"{set_name} does not list arm {bad}")
    tree = layout.tree(ws)
    preflight(tree, task_set, names, agent.route, stream)
    out = []
    runner = runner_for(agent)
    for arm in [_arm(a) for a in names]:
        for variant in sorted({v for e in task_set.tasks for v in layout.variants(tree, e.task, arm.name)}, key=lambda v: v or ""):
            job = Job(ws, set_name, agent, arm, variant)
            runner.prepare(job)
            runner.run(job)
            runner.collect(job)
            print(f"{job.name}: done", file=stream)
            out.append(job.folder)
    return out


def score(set_name: str, ws=None, stream=None) -> int:
    from medomni.bench.scoring import score_run

    stream = stream or sys.stdout
    ws = ws or workspace.load()
    task_set, _ = load_set(set_name)
    h = task_set_hash(task_set)
    jobs = sorted(p for p in Path(ws.runs).glob(f"{set_name.replace('/', '.')}--*") if (p / "runs.jsonl").is_file())
    if not jobs:
        print(f"no runs of {set_name} under {ws.runs}", file=stream)
        return 1
    n = 0
    for job in jobs:
        rows = score_run(job, layout.tree(ws) / layout.CONTENT, h, Path(ws.results))
        n += len(rows)
    print(f"{set_name}: {n} score rows written to {ws.results}", file=stream)
    return 0
