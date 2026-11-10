"""MedOmni's v1 builder's side of each arm (R-143 c): what it hides or shows in a built task. Registered in
`medomni.arm_builds` as `medomni-v1:<arm>`; the arm's run side is the object registered under its name in `medomni.arms`.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ArmBuild:
    name: str
    tools_block: str = "tools.md"
    extra_block: str | None = None

    def variants(self, pair) -> tuple[str | None, ...]:
        return (None,)

    def mask(self, record: dict, variant, pair) -> dict:
        return record

    def definition(self, pair, variant) -> dict[str, bytes | Path]:
        """Config files of this arm under this variant (R-111), by name."""
        return {f"arm:{self.name}": (self.name + "\n").encode()} | ({"arm-variant": str(variant).encode()} if variant else {})

    def check(self, pair, variant, inv: dict, subject: str) -> list[str]:
        return []


RUNGS = ("r1", "r2", "r3", "r4", "r5", "r6")


class LadderBuild(ArmBuild):
    """Cumulative rungs r1-r6 over one complete-case cohort (R-4). Rungs and masks are in `arms/modality-ladder.yaml`
    beside the cohort (R-89). Every rung is cut from the same content, so what a lower rung keeps is byte-identical
    at every higher rung."""

    def spec(self, pair) -> dict:
        return yaml.safe_load((pair.folder / "arms" / "modality-ladder.yaml").read_text(encoding="utf-8"))

    def variants(self, pair) -> tuple[str, ...]:
        return RUNGS

    def allowed(self, spec: dict, rung: str) -> dict:
        out = {"families": set(), "tables": set(), "measurements_from": set(), "all_tables": False, "rest": False}
        for r in RUNGS[: RUNGS.index(rung) + 1]:
            e = spec["rungs"][r]
            out["families"] |= set(e.get("families", []))
            out["tables"] |= set(e.get("tables", []))
            out["measurements_from"] |= set(e.get("measurements_from", []))
            out["all_tables"] |= bool(e.get("all_tables"))
            out["rest"] |= bool(e.get("rest"))
        return out

    def _drop_masked(self, rec: dict, pair, codes: list[str]) -> None:
        from .content import table_specs
        from .evidence import drops

        specs = table_specs(pair)
        for name, t in rec["tables"].items():
            if name in specs:
                t["rows"] = [r for r in t["rows"] if not drops(specs[name], dict(zip(t["head"], r)), codes)]

    def mask(self, record: dict, variant, pair) -> dict:
        spec = self.spec(pair)
        a = self.allowed(spec, variant)
        rec = copy.deepcopy(record)
        if spec.get("masks"):
            self._drop_masked(rec, pair, spec["masks"])
        if a["rest"]:
            return rec
        keep = a["families"]
        rec["files"] = [f for f in rec["files"] if f["family"] in keep]
        if not a["all_tables"]:
            rec["tables"] = {n: t for n, t in rec["tables"].items() if n in a["tables"]}
        if rec["measurements"] is not None:
            if "clinical-measurement-irregular" not in keep:
                rec["measurements"] = None
            elif a["measurements_from"]:
                rec["measurements"] = [m for m in rec["measurements"] if m["_from"] in a["measurements_from"]]
        return rec

    def definition(self, pair, variant) -> dict[str, bytes | Path]:
        repo = pair.package.parent.parent.parent
        path = pair.folder / "arms" / "modality-ladder.yaml"
        return super().definition(pair, variant) | {path.relative_to(repo).as_posix(): path}

    def check(self, pair, variant, inv: dict, subject: str) -> list[str]:
        """A rung must carry every complete-case family it allows."""
        from .contracts.recipe import Files

        a = self.allowed(self.spec(pair), variant)
        complete = {f for q in pair.cohort.require if isinstance(q, Files) for f in q.files}
        missing = (complete if a["rest"] else complete & a["families"]) - set(inv["families"])
        return [f"{pair.id} {variant}: patient lacks {sorted(missing)} after staging"] if missing else []


encoders = ArmBuild("encoders")
no_perception = ArmBuild("no-perception", tools_block="tools.noenc.md")
encoders_required = ArmBuild("encoders-required", extra_block="tools.forced.md")
modality_ladder = LadderBuild("modality-ladder", tools_block="tools.ladder.md")
