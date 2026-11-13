"""v0.2 agent configs -> v0.3 agent configs (`bench/agents/<name>.yaml`).

One v0.3 config is assembled from three v0.2 files:

- `harness/harbor/agents/<name>.yaml`: scaffold, model, env, max_turns, api_base
- `harness/models.yaml`: `served`, the model names the provider reports back
- `harness/experiments/*.yaml`: `expect.<name>.model_served`, for agents with no models.yaml entry

`route` is new in v0.3 (U2.10): `local` for an agent whose `api_base` is this machine, else `cloud`.
"""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import yaml

AGENTS = "harness/harbor/agents"
MODELS = "harness/models.yaml"
EXPERIMENTS = "harness/experiments"
DEST = "bench/agents"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _served(repo: Path) -> tuple[dict[str, list[str]], dict[str, set[str]]]:
    from_models = {}
    for m in yaml.safe_load((repo / MODELS).read_text())["models"].values():
        from_models[Path(m["agent_config"]).stem] = list(m["served"])
    from_expect: dict[str, set[str]] = {}
    for p in sorted((repo / EXPERIMENTS).glob("*.yaml")):
        exp = yaml.safe_load(p.read_text()) or {}
        for agent, e in (exp.get("expect") or {}).items():
            if isinstance(e, dict) and e.get("model_served"):
                from_expect.setdefault(agent, set()).add(e["model_served"])
    return from_models, from_expect


def convert(repo: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    repo = Path(repo)
    from_models, from_expect = _served(repo)
    outputs, notes = {}, {}
    for path in sorted((repo / AGENTS).glob("*.yaml")):
        name = path.stem
        (agent,) = yaml.safe_load(path.read_text())["agents"]
        kwargs = dict(agent.get("kwargs") or {})
        api_base = kwargs.pop("api_base", None)
        max_turns = kwargs.pop("max_turns", None)
        if kwargs:
            raise ValueError(f"{path}: kwargs not mapped: {sorted(kwargs)}")
        local = api_base is not None and urlparse(api_base).hostname in LOCAL_HOSTS
        if name in from_models:
            served, served_from = from_models[name], MODELS
        elif len(from_expect.get(name, ())) == 1:
            served, served_from = sorted(from_expect[name]), EXPERIMENTS
        else:
            raise ValueError(f"{name}: no single served model name in {MODELS} or {EXPERIMENTS}")
        settings = {"scaffold": agent["name"], "model_served": served[0] if len(served) == 1 else served,
                    "env": dict(agent.get("env") or {})}
        if max_turns is not None:
            settings["max_turns"] = max_turns
        if api_base is not None:
            settings["api_base"] = api_base
        data = {"kind": "agent", "name": name, "model": agent["model_name"], "route": "local" if local else "cloud"}
        if agent["model_name"] == "openai/replay":  # v0.2's replay check: no model behind it (R-145)
            data["runner"] = "replay"
        data["settings"] = settings
        outputs[f"{DEST}/{name}.yaml"] = data
        notes[name] = {"route": data["route"], "model_served_from": served_from}
    return outputs, notes
