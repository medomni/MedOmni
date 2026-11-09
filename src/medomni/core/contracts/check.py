"""`medomni contracts check [<contract> ...]`: validate every contract file in the repository and installed plug-ins.

Content files are found by the repository layout (R-1, R-44). Plug-in folders use the same layout and are read the same
way (R-69); family files come from the repository only, and benchmarks with their task sets from both (R-77, R-83). The repository's
model cards are checked from Stage 3 part 1 (R-66); dataset packages, templates and cohorts from part 2 (R-68).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from medomni.core import plugins

from . import (AgentConfig, AliasFile, BenchmarkCard, Cohort, CohortTests, ContractError, DatasetConfig, DatasetPolicy,
               EvidenceRules, FamilyFile, LabelLibrary, ModelCard, TaskSet, TaskTemplate, load)

REPO, PLUGINS, BOTH = "repo", "plugins", "both"


@dataclass(frozen=True)
class Content:
    contract: str
    pattern: str  # glob under a content root
    model: type
    exclude: tuple[str, ...] = ()
    where: str = BOTH  # which roots the pattern is read in


CONTENT = (
    Content("family registry", "core/families/*.yaml", FamilyFile, exclude=("aliases.yaml",), where=REPO),
    Content("family registry", "core/families/aliases.yaml", AliasFile, where=REPO),
    Content("agent config", "bench/agents/*.yaml", AgentConfig),
    Content("benchmark", "bench/benchmarks/*/benchmark.yaml", BenchmarkCard),
    Content("task set", "bench/benchmarks/*/sets/*.yaml", TaskSet),
    Content("dataset config", "bench/datasets/*/dataset.yaml", DatasetConfig),
    Content("dataset policy", "bench/datasets/*/policy.yaml", DatasetPolicy),
    Content("recipe", "bench/datasets/*/labels.yaml", LabelLibrary),
    Content("recipe", "bench/datasets/*/evidence.yaml", EvidenceRules),
    Content("task template", "bench/datasets/*/tasks/*/template.yaml", TaskTemplate),
    Content("recipe", "bench/datasets/*/tasks/*/cohorts/*.tests.yaml", CohortTests),
    Content("recipe", "bench/datasets/*/tasks/*/cohorts/*.yaml", Cohort, exclude=("*.tests.yaml",)),
    Content("model card", "perception/encoders/*/*/card.yaml", ModelCard),  # the repository's since Stage 3 part 1 (R-66)
)

# Short names accepted on the command line, as on the reference pages
ALIASES = {"families": "family registry", "agents": "agent config", "benchmarks": "benchmark", "sets": "task set", "templates": "task template",
           "recipes": "recipe", "datasets": "dataset config", "policies": "dataset policy", "cards": "model card"}


@dataclass(frozen=True)
class Result:
    package: str
    contract: str
    path: Path
    label: str  # repository-relative path, or `<package>:<path in its folder>`
    error: str | None


def results(roots: list[tuple[str, Path]], only: set[str] | None = None):
    """Validate every contract file under the roots (repository first, then plug-in folders)."""
    for package, root in roots:
        builtin = package == plugins.BUILTIN
        for c in CONTENT:
            if (only and c.contract not in only) or c.where == (PLUGINS if builtin else REPO):
                continue
            for p in sorted(root.glob(c.pattern)):
                if any(p.match(x) for x in c.exclude):
                    continue
                rel = p.relative_to(root).as_posix()
                label = rel if builtin else f"{package}:{rel}"
                try:
                    load(p, c.model)
                    yield Result(package, c.contract, p, label, None)
                except ContractError as e:
                    yield Result(package, c.contract, p, label, str(e))


def check(repo: Path | None, only: set[str] | None = None, out=None) -> tuple[dict[str, list[int]], int]:
    """Returns ({contract: [ok, failed]}, failures)."""
    out = out or sys.stdout
    roots, bad = plugins.roots(repo)
    counts: dict[str, list[int]] = {}
    failed = 0
    for f in bad:
        failed += 1
        print(f"FAIL  {f.error}", file=out)
    for r in results(roots, only):
        c = counts.setdefault(r.contract, [0, 0])
        if r.error is None:
            c[0] += 1
            print(f"ok    {r.label}", file=out)
        else:
            c[1] += 1
            failed += 1
            print(f"FAIL  {r.error}", file=out)
    return counts, failed


def main(argv: list[str]) -> int:
    if argv and argv[0] in ("-h", "--help"):
        print("usage: medomni contracts check [<contract> ...]\n\nValidates every contract file in the repository (when run "
              "inside one) and in the installed plug-in folders.\nContracts: " + ", ".join(sorted(ALIASES)))
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
    counts, failed = check(plugins.find_repo(), only)
    passed = sum(ok for ok, _ in counts.values())
    total = sum(ok + bad for ok, bad in counts.values())
    summary = ", ".join(f"{k} {ok}/{ok + bad}" for k, (ok, bad) in sorted(counts.items())) or "no files"
    print(f"{passed}/{total} files pass: {summary}")
    return 1 if failed else 0
