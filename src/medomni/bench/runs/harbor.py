"""The agent runner: Harbor, behind the one runner interface (R-118). `prepare` writes the job file, `run` launches Harbor,
`collect` reads each trial into run and prediction records. Scores come only from the scorer.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from importlib.resources import files
from pathlib import Path

import re

import yaml
from pydantic import Field, model_validator

from medomni.core.contracts import Contract, load_data
from medomni.core.contracts.base import NonEmpty

from . import write_records


class HarborSettings(Contract):
    """An agent config's `settings` for this runner (R-145): Harbor's agent block."""

    scaffold: NonEmpty  # a Harbor agent, such as terminus-2
    model_served: NonEmpty | tuple[NonEmpty, ...]  # what the provider reports back; some report two spellings
    env: dict[str, str] = {}
    max_turns: int | None = Field(default=None, ge=1)
    api_base: str | None = None
    route: str = "local"  # copied from the agent config to check keys; not written

    @model_validator(mode="after")
    def _keys_by_reference(self):
        if self.route == "cloud":
            bad = [k for k, v in self.env.items() if not re.match(r"^\$\{[A-Z][A-Z0-9_]*\}$", v)]
            if bad:
                raise ValueError(f"a cloud agent names keys only as ${{VARNAME}}; literal values in {bad}")
        return self


def settings_of(agent) -> HarborSettings:
    return load_data({**agent.settings, "route": agent.route}, HarborSettings, f"agent {agent.name}: settings")

AGENT_FAILURES = {"VerifierOutputParseError", "AgentTimeoutError", "RewardFileNotFoundError", "RewardFileEmptyError", "VerifierTimeoutError"}


def classify_error(err) -> str | None:
    """`agent`: the agent never produced a valid submission, a real result. Anything else is ours and blocks the score."""
    if not err:
        return None
    kind = err.get("exception_type") if isinstance(err, dict) else str(err).split(":", 1)[0].strip()
    return "agent" if kind in AGENT_FAILURES else "infra"


def agent_block(agent) -> dict:
    h = settings_of(agent)
    block = {"name": h.scaffold, "model_name": agent.model}
    kwargs = {}
    if h.max_turns:
        kwargs["max_turns"] = h.max_turns
    if h.api_base:
        kwargs["api_base"] = h.api_base
    if kwargs:
        block["kwargs"] = kwargs
    if h.env:
        block["env"] = dict(h.env)
    return block


def job_config(job) -> dict:
    """Harbor's job file: the base settings, this agent, and exactly this job's atom folders."""
    base = yaml.safe_load(files("medomni.bench.runs").joinpath("assets/harbor/base.yaml").read_text(encoding="utf-8"))
    return {**base, "job_name": job.name, "jobs_dir": str(job.folder.parent), "agents": [agent_block(job.agent)],
            "tasks": [{"path": str(d)} for _, _, d in job.atoms()]}


def trial_atom(trial: Path) -> str | None:
    """A trial's atom, from Harbor's own record: trial folder names truncate task ids."""
    result = trial / "result.json"
    if not result.is_file():
        return None
    task = json.loads(result.read_text(encoding="utf-8")).get("task_id")
    path = task.get("path") if isinstance(task, dict) else task
    return Path(str(path)).name if path else None


def served_model(trial: Path):
    p = trial / "agent/trajectory.json"
    if not p.is_file():
        return None
    names = sorted({s.get("model_name") for s in (json.loads(p.read_text(encoding="utf-8")) or {}).get("steps", []) if s.get("model_name")})
    return names[0] if len(names) == 1 else None


class Harness:
    name = "agent"
    settings = HarborSettings  # what an agent config's `settings` holds for this runner

    def prepare(self, job) -> None:
        job.folder.mkdir(parents=True, exist_ok=True)
        (job.folder / "job.yaml").write_text(yaml.safe_dump(job_config(job), sort_keys=False), encoding="utf-8")

    def run(self, job) -> None:
        if shutil.which("harbor") is None:
            raise RuntimeError("Harbor isn't installed here (see Run your agent)")
        subprocess.run(["harbor", "run", "-c", str(job.folder / "job.yaml")], check=True)

    def collect(self, job) -> None:
        by_atom = {atom: (pair, d) for pair, atom, d in job.atoms()}
        trials = []
        for trial in sorted(p for p in job.folder.iterdir() if p.is_dir()):
            atom = trial_atom(trial)
            if atom not in by_atom:
                continue
            result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
            served = served_model(trial)
            declared = settings_of(job.agent).model_served
            allowed = (declared,) if isinstance(declared, str) else declared
            mismatch = served is not None and served not in allowed
            error = "infra" if mismatch else classify_error(result.get("exception_info"))
            trials.append((by_atom[atom][0], atom, trial, error, served))
        write_records(job, trials)


harness = Harness()
