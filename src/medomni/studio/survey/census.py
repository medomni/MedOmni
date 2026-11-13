"""`medomni studio census <set>`: per built pair and arm, the families staged and the target counts over the pool (v0.2's two census copies, merged)."""
from __future__ import annotations

import json

from .. import common
from ..tools import Result, Survey


class Census(Survey):
    name = "census"
    summary = "per built pair and arm: families staged and the answers' spread"
    target = "set"
    target_help = "<benchmark>/<set> or one <template>@<cohort>"

    def make(self, target, a, ctx) -> Result:
        rows, doc = [], {}
        for pair in common.pairs_of(target):
            meta = common.content(ctx.ws, pair)
            if meta is None:
                rows.append([pair, "—", "not built", "—"])
                continue
            per_arm: dict = {}
            for arm, variant, _, d in common.built_atoms(ctx.ws, pair, meta):
                inv = json.loads((d / "data/inventory.json").read_text(encoding="utf-8"))
                per_arm.setdefault(f"{arm}/{variant}" if variant else arm, set()).update(inv["families"])
            counts = {t: s["counts"] for t, s in meta["pool_stats"].items()}
            doc[pair] = {"families": {a: sorted(f) for a, f in per_arm.items()}, "answers": counts, "pool": meta["counts"]}
            for arm, fams in sorted(per_arm.items()):
                rows.append([pair, arm, len(fams), "; ".join(f"{t} {c}" for t, c in counts.items())])
        by_dataset = common.group([r for r in rows if r[1] != "—"], lambda r: (r[0].split("_")[0], r[1]))
        lines = [common.table(["pair", "arm", "families", "answers over the pool"], rows), ""]
        for (dataset, arm), rs in sorted(by_dataset.items()):
            sets = {frozenset(doc[r[0]]["families"].get(arm, ())) for r in rs}
            lines.append(f"{dataset} {arm}: {len(rs)} pairs, uniform={'yes' if len(sets) == 1 else f'no ({len(sets)} distinct sets)'}")
        slug = target.replace("/", "_").replace("@", "_")
        text = "\n".join(lines)
        return Result(text, {f"{slug}.json": json.dumps(doc, indent=1) + "\n", f"{slug}.md": text + "\n"})
