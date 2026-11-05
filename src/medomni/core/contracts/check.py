"""`medomni contracts check [<contract> ...]`: validate every contract file in the repository and installed plug-ins.

Content files are found by the repository layout (R-1, R-44). Perception's model cards join in Stage 3, when the
converted cards are committed (R-66); dataset packages, templates and cohorts join with them (R-68).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from medomni.core import plugins

from . import (AgentConfig, AliasFile, Cohort, CohortTests, ContractError, DatasetConfig, DatasetPolicy,
               EvidenceRules, FamilyFile, LabelLibrary, ModelCard, TaskSet, TaskTemplate, load, load_data)


@dataclass(frozen=True)
class Content:
    contract: str
    pattern: str  # glob under the repository root
    model: type
    exclude: tuple[str, ...] = ()


CONTENT = (
    Content("family registry", "core/families/*.yaml", FamilyFile, exclude=("aliases.yaml",)),
    Content("family registry", "core/families/aliases.yaml", AliasFile),
    Content("agent config", "bench/agents/*.yaml", AgentConfig),
    Content("task set", "bench/sets/*.yaml", TaskSet),
    Content("dataset config", "bench/datasets/*/dataset.yaml", DatasetConfig),
    Content("dataset policy", "bench/datasets/*/policy.yaml", DatasetPolicy),
    Content("recipe", "bench/datasets/*/labels.yaml", LabelLibrary),
    Content("recipe", "bench/datasets/*/evidence.yaml", EvidenceRules),
    Content("task template", "bench/datasets/*/tasks/*/template.yaml", TaskTemplate),
    Content("recipe", "bench/datasets/*/tasks/*/cohorts/*.tests.yaml", CohortTests),
    Content("recipe", "bench/datasets/*/tasks/*/cohorts/*.yaml", Cohort, exclude=("*.tests.yaml",)),
)

# Plug-in kinds whose pieces are one contract file each. A piece is a path to the file.
PLUGIN_KINDS = {plugins.AGENTS: AgentConfig, plugins.ENCODERS: ModelCard}

# Short names accepted on the command line, as on the reference pages
ALIASES = {"families": "family registry", "agents": "agent config", "sets": "task set", "templates": "task template",
           "recipes": "recipe", "datasets": "dataset config", "policies": "dataset policy", "cards": "model card"}


def find_repo(start: Path | None = None) -> Path:
    p = (start or Path.cwd()).resolve()
    for d in (p, *p.parents):
        f = d / "pyproject.toml"
        if f.is_file() and 'name = "medomni"' in f.read_text(encoding="utf-8"):
            return d
    raise FileNotFoundError("not inside a MedOmni repository (no pyproject.toml for medomni found)")


def files(repo: Path, only: set[str] | None = None):
    for c in CONTENT:
        if only and c.contract not in only:
            continue
        for p in sorted(repo.glob(c.pattern)):
            if any(p.match(x) for x in c.exclude):
                continue
            yield c.contract, p, c.model


def check(repo: Path, only: set[str] | None = None, out=sys.stdout) -> tuple[dict[str, list[int]], int]:
    """Returns ({contract: [ok, failed]}, failures)."""
    counts: dict[str, list[int]] = {}
    failed = 0
    for contract, path, model in files(repo, only):
        c = counts.setdefault(contract, [0, 0])
        try:
            load(path, model)
            c[0] += 1
            print(f"ok    {path.relative_to(repo)}", file=out)
        except ContractError as e:
            c[1] += 1
            failed += 1
            print(f"FAIL  {e}", file=out)
    for group, model in PLUGIN_KINDS.items():
        contract = {AgentConfig: "agent config", ModelCard: "model card"}[model]
        if only and contract not in only:
            continue
        r = plugins.resolve(group)
        for piece in r.pieces.values():
            if piece.builtin:
                continue
            c = counts.setdefault(contract, [0, 0])
            try:
                obj = piece.load()
                if isinstance(obj, (str, Path)):
                    load(Path(obj), model)
                else:
                    load_data(obj, model, piece.full_name)
                c[0] += 1
                print(f"ok    {piece.full_name}", file=out)
            except (plugins.PluginError, ContractError) as e:
                c[1] += 1
                failed += 1
                print(f"FAIL  {e}", file=out)
    return counts, failed


def main(argv: list[str]) -> int:
    if argv and argv[0] in ("-h", "--help"):
        print("usage: medomni contracts check [<contract> ...]\n\nValidates every contract file in the repository and "
              "the installed plug-in packages.\nContracts: " + ", ".join(sorted(ALIASES)))
        return 0
    if not argv or argv[0] != "check":
        print("usage: medomni contracts check [<contract> ...]", file=sys.stderr)
        return 2
    names = argv[1:]
    unknown = [n for n in names if n not in ALIASES and n not in ALIASES.values()]
    if unknown:
        print(f"medomni contracts check: unknown contract {', '.join(unknown)}", file=sys.stderr)
        return 2
    only = {ALIASES.get(n, n) for n in names} or None
    try:
        repo = find_repo()
    except FileNotFoundError as e:
        print(f"medomni contracts check: {e}", file=sys.stderr)
        return 2
    counts, failed = check(repo, only)
    total = sum(ok + bad for ok, bad in counts.values())
    summary = ", ".join(f"{k} {ok}/{ok + bad}" for k, (ok, bad) in sorted(counts.items())) or "no files"
    print(f"{total - failed}/{total} files pass: {summary}")
    return 1 if failed else 0
