"""The workspace config (U2.7): where your data copies, cache, built tasks, runs and results are.

It is `$MEDOMNI_HOME/workspace.yaml` when `MEDOMNI_HOME` is set, else `~/.medomni/workspace.yaml` (Get started page).
Every path in it is absolute. There is no default data path: a dataset is used only once its path is set.
API keys are never in the config: export them in your shell (R-159).
"""
from __future__ import annotations

import os
from pathlib import Path

ENV = "MEDOMNI_HOME"
FILE = "workspace.yaml"


class WorkspaceError(LookupError):
    pass


def home() -> Path:
    """The workspace folder: `$MEDOMNI_HOME`, else `~/.medomni`."""
    value = os.environ.get(ENV)
    if value:
        p = Path(value)
        if not p.is_absolute():
            raise WorkspaceError(f"{ENV} must be an absolute path, not '{value}'")
        return p
    return Path.home() / ".medomni"


def config_path() -> Path:
    return home() / FILE


def load(path: Path | None = None):
    """The workspace config, checked against its contract (`WorkspaceConfig`)."""
    from medomni.core.contracts import WorkspaceConfig, load as load_contract

    p = Path(path) if path is not None else config_path()
    if not p.is_file():
        where = f"set {ENV}, or write ~/.medomni/{FILE}" if path is None and not os.environ.get(ENV) else \
            f"write {p}"
        raise WorkspaceError(f"no workspace config at {p}; {where} (see Get started)")
    return load_contract(p, WorkspaceConfig)


def dataset_path(config, dataset: str) -> Path:
    try:
        return Path(config.datasets[dataset].path)
    except KeyError:
        raise WorkspaceError(f"dataset '{dataset}' has no path in the workspace config (datasets.{dataset}.path)") \
            from None
