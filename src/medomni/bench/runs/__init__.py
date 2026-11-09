"""Run an intelligence on a set's rendered tasks (R-77, R-118). One runner interface: prepare, run, collect."""
from __future__ import annotations

import csv
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Protocol, runtime_checkable

from medomni import __version__
from medomni.bench.build import _arm, _atom_dir, _tree
from medomni.bench.build.content import atom_name as _atom_name
from medomni.bench.build.pool import BuildError
from medomni.bench.build.sets import load_set, task_set_hash
from medomni.core import plugins, workspace
from medomni.core.contracts import AgentConfig, load


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
        self.tree = _tree(ws)
        condition = f"{arm.name}.{variant}" if variant else arm.name
        self.name = "--".join([set_name.replace("/", "."), agent.name, condition, f"r{rep}", self.stamp])
        self.folder = Path(ws.runs) / self.name

    def atoms(self) -> list[tuple[str, str, Path]]:
        """(pair, atom name, rendered folder) of every atom of the set under this arm."""
        out = []
        for e in self.task_set.tasks:
            meta = json.loads((self.tree / "_content" / e.task / "content.json").read_text(encoding="utf-8"))
            for a in meta["atoms"]:
                d = _atom_dir(self.tree, self.arm, self.variant, a["atom"])
                if not d.is_dir():
                    raise BuildError(f"{a['atom']}: not built under {self.arm.name}; run `medomni bench task build --set {self.set_name}`")
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
    """`runs.jsonl` and `predictions.jsonl` from finished trials: (pair, atom, trial folder, error kind, model served)."""
    from medomni.core.contracts import IntelligenceRef, PredictionRecord, RunRecord, load_data

    job.folder.mkdir(parents=True, exist_ok=True)
    hashes, versions = {}, {}
    who = load_data({"kind": "agent", "name": job.agent.name}, IntelligenceRef, "intelligence").model_dump(mode="json")
    key = f"{job.arm.name}/{job.variant}" if job.variant else job.arm.name
    with open(job.folder / "runs.jsonl", "w", encoding="utf-8") as runs, open(job.folder / "predictions.jsonl", "w", encoding="utf-8") as preds:
        for pair, atom, trial, error, served in trials:
            content = job.tree / "_content" / pair
            if pair not in hashes:
                hashes[pair] = json.loads((content / "manifest.json").read_text(encoding="utf-8"))["config_hash"][key]
                versions[pair] = json.loads((content / "content.json").read_text(encoding="utf-8"))["version"]
            run_id = f"{job.name}/{atom}"
            doc = {"kind": "run", "run_id": run_id, "release": __version__, "task_set": job.set_name,
                   "task": pair, "task_version": versions[pair], "config_hash": hashes[pair], "intelligence": who,
                   "model_served": served, "error_kind": error, "agent": {"arm": job.arm.name, "arm_variant": job.variant}}
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
    path = plugins.find_repo() / "bench/agents" / f"{name}.yaml"
    if not path.is_file():
        raise BuildError(f"no agent {name} at {path}")
    return load(path, AgentConfig)


def runner_for(agent: AgentConfig) -> Runner:
    """The replay agent runs with no Harbor; every other agent runs under the Harbor harness."""
    pieces = plugins.resolve(plugins.RUNNERS).pieces
    return pieces["replay" if agent.model == "openai/replay" else "agent"].load()


def run(set_name: str, agent_name: str, arms: list[str] | None = None, ws=None, stream=None) -> list[Path]:
    stream = stream or sys.stdout
    ws = ws or workspace.load()
    agent = load_agent(agent_name)
    task_set, _ = load_set(set_name)
    names = arms or list(task_set.arms)
    bad = sorted(set(names) - set(task_set.arms))
    if bad:
        raise BuildError(f"{set_name} does not list arm {bad}")
    out = []
    runner = runner_for(agent)
    for arm in [_arm(a) for a in names]:
        for variant in arm.variants(_Any()):
            job = Job(ws, set_name, agent, arm, variant)
            runner.prepare(job)
            runner.run(job)
            runner.collect(job)
            print(f"{job.name}: done", file=stream)
            out.append(job.folder)
    return out


class _Any:
    """An arm's variants don't depend on the pair for the arms that ship; a pair is only needed for its definition file."""


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
        rows = score_run(job, _tree(ws) / "_content", h, Path(ws.results))
        n += len(rows)
    print(f"{set_name}: {n} score rows written to {ws.results}", file=stream)
    return 0
