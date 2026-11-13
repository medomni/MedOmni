"""The route check (Bosong, 2026-11-10): before a run, the agent's route against each dataset policy of the set.

Each built task names the datasets its atoms hold data from (`content.json`'s `datasets`). For each, the dataset's
`policy.yaml` gives the route: `deny` refuses the run; `conditional` runs and prints the condition the user must meet;
`allow` runs. A dataset with no policy, or a task that names no dataset, refuses any route but `local`, since its rules
can't be read.
"""
from __future__ import annotations

from pathlib import Path

from medomni.core.contracts import BuiltContent, DatasetPolicy, load
from medomni.core.tasks import layout


def _policy(dataset: str) -> DatasetPolicy | None:
    from medomni.core.loading import find_package

    try:
        p = find_package(dataset) / "policy.yaml"
    except FileNotFoundError:
        return None
    return load(p, DatasetPolicy) if p.is_file() else None


def check(tree: Path, tasks: list[str], route: str) -> tuple[list[str], list[str]]:
    """(problems that refuse the run, conditions to print), each naming the dataset."""
    problems, conditions, seen = [], [], {}
    for task in tasks:
        content = load(layout.content_dir(tree, task) / "content.json", BuiltContent)
        if not content.datasets and route != "local":
            problems.append(f"route: {task} names no dataset, so a {route} route can't be checked")
        for ds in content.datasets:
            if ds not in seen:
                seen[ds] = _policy(ds)
                policy = seen[ds]
                if policy is None:
                    if route != "local":
                        problems.append(f"route: {ds} has no policy.yaml, so a {route} route can't be checked")
                    continue
                rule = getattr(policy.routes, route)
                if rule == "deny":
                    problems.append(f"route: {ds}'s policy denies the {route} route")
                elif rule == "conditional":
                    conditions.append(f"{ds}, {route} route: {policy.route_conditions.get(route, 'see its policy.yaml')}")
    return problems, conditions
