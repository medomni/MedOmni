"""The four built-in arms (R-84, R-85). An arm supplies a description, what it changes in the rendered atom task, and
(part 5) what the run attaches. Build finds an arm by its registered name only.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Arm:
    name: str
    description: str
    perception: str = "on"  # on, off, forced
    max_calls: int | None = 300  # the sidecar's call budget; None: no sidecar
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


class ModalityLadder(Arm):
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
        from medomni.bench.build.content import table_specs
        from medomni.bench.build.evidence import drops

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
        from medomni.core.contracts.recipe import Files

        a = self.allowed(self.spec(pair), variant)
        complete = {f for q in pair.cohort.require if isinstance(q, Files) for f in q.files}
        missing = (complete if a["rest"] else complete & a["families"]) - set(inv["families"])
        return [f"{pair.id} {variant}: patient lacks {sorted(missing)} after staging"] if missing else []


encoders = Arm("encoders", "The agent has the record and the perception service's encoders.")
no_perception = Arm("no-perception", "The agent has the record and no encoders.", perception="off", max_calls=None,
                    tools_block="tools.noenc.md")
encoders_required = Arm("encoders-required", "As encoders, with one required encoder call and a larger call budget.",
                        perception="forced", max_calls=1000, extra_block="tools.forced.md")
modality_ladder = ModalityLadder("modality-ladder", "Six cumulative levels of the record, from demographics to everything.",
                                 tools_block="tools.ladder.md")
