"""`medomni studio build-sheet <set>`: what a set's build made, per pair and arm, read from what the build wrote
(content.json, manifest.json, inventory.json), never from a declaration."""
from __future__ import annotations

import collections
import json

from .. import common
from ..tools import Report, Result


class BuildSheet(Report):
    name = "build-sheet"
    summary = "write a sheet of what a set's build made, per task"
    target = "set"
    target_help = "<benchmark>/<set> or one <template>@<cohort>"

    def make(self, target, a, ctx) -> Result:
        rows, doc, fam_rows = [], {}, collections.defaultdict(collections.Counter)
        for pair in common.pairs_of(target):
            meta, man = common.content(ctx.ws, pair), common.manifest(ctx.ws, pair)
            if meta is None:
                rows.append([pair, "not built", 0, 0, "—", "—"])
                continue
            per = collections.defaultdict(lambda: [0, set()])
            for arm, variant, _, d in common.built_atoms(ctx.ws, pair, meta):
                key = f"{arm}/{variant}" if variant else arm
                inv = json.loads((d / "data/inventory.json").read_text(encoding="utf-8"))
                per[key][0] += 1
                per[key][1] |= set(inv["families"])
                for fam in inv["families"]:
                    fam_rows[pair][fam] += 1
            short = [t["name"] for t in meta["targets"] if t.get("too_few")]
            hashes = (man or {}).get("config_hash", {})
            for arm, (n, fams) in sorted(per.items()) or [("—", (0, set()))]:
                rows.append([pair, arm, n, len(meta["targets"]), ", ".join(short) or "—", (hashes.get(arm) or "—")[:17]])
            doc[pair] = {"atoms": len(meta["atoms"]), "targets": [t["name"] for t in meta["targets"]], "counts": meta["counts"],
                         "marked": short, "arms": {k: {"atoms": v[0], "families": sorted(v[1])} for k, v in per.items()}}
        fams = sorted({f for c in fam_rows.values() for f in c})
        lines = [f"# Build sheet: {target}", "", common.table(["pair", "arm", "atoms", "targets", "marked too few", "config hash"], rows), ""]
        if fams:
            lines += ["## Family × pair coverage (atoms staging the family)", "",
                      common.table(["family", *sorted(fam_rows)], [[f, *[fam_rows[p][f] for p in sorted(fam_rows)]] for f in fams])]
        text = "\n".join(lines) + "\n"
        slug = target.replace("/", "_").replace("@", "_")
        return Result(text, {f"{slug}.md": text, f"{slug}.json": json.dumps(doc, indent=1, default=str) + "\n"})
