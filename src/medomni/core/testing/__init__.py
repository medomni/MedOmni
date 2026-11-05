"""The testing kit: the checks MedOmni's CI runs, for plug-in packages to run in their own CI.

Projects and plug-in packages register checks in the `medomni.checks` entry-point group. A check is a callable
that takes no arguments and raises on failure.
"""
from __future__ import annotations

from dataclasses import dataclass

from medomni.core import plugins


@dataclass(frozen=True)
class CheckResult:
    name: str  # <package>:<name>
    ok: bool
    message: str = ""


def checks() -> plugins.Resolved:
    return plugins.resolve(plugins.CHECKS)


def run_checks(names: list[str] | None = None) -> list[CheckResult]:
    """Run every registered check, or only those named (short or full names)."""
    r = checks()
    results = [CheckResult(p.full_name, False, msg) for p, msg in r.errors]
    for name, piece in sorted(r.pieces.items()):
        if names and name not in names and piece.full_name not in names:
            continue
        try:
            piece.load()()
            results.append(CheckResult(piece.full_name, True))
        except Exception as e:  # a failing check is a result, not a crash
            results.append(CheckResult(piece.full_name, False, f"{type(e).__name__}: {e}"))
    return results
