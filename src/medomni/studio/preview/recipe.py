"""`medomni studio preview <template>@<cohort>`: run a cohort up to the draw on your copy and print the patients left
after each step and per class (R-33). Builds nothing; conversions the file check needs go to the cache, as a build's would."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .. import common
from ..tools import Preview, Result


class RecipePreview(Preview):
    name = "preview"
    summary = "run a cohort up to the draw and print the patients left after each step and per class"
    target = "pair"
    target_help = "<template>@<cohort>"

    def options(self, p) -> None:
        p.add_argument("--no-file-check", action="store_true", help="skip the conversions of a `converts` requirement")

    def make(self, target, a, ctx) -> Result:
        from medomni.bench.build import BuildError, content
        from medomni.bench.build.pool import cell_of, draw, event_subjects, file_checker, pool, read_events, source_ids
        from medomni.core import workspace
        from medomni.core.cache import Cache
        from medomni.core.loading import build

        pair = common.load_pair(target)
        cache = Cache(Path(ctx.ws.cache))
        raw = workspace.dataset_path(ctx.ws, pair.dataset)
        entry, _ = build(pair.package, raw, cache, pair.dataset)
        path = entry.path / "events.parquet"
        source = source_ids(pair, event_subjects(path))
        result = pool(pair, read_events(path, source), source)
        try:
            drawn = len(draw(result, None if a.no_file_check else file_checker(pair, raw, cache)))
            verdict = f"draw: {drawn} of {pair.cohort.select.n}"
        except BuildError as e:
            verdict = f"draw: would refuse: {e}"
        cells = defaultdict(int)
        for p in result.patients.values():
            cells[cell_of(p, pair.cohort)] += 1
        stats = content.pool_stats(result)
        lines = [f"{target}"] + [f"  {step}: {n}" for step, n in result.counts.items()] + [f"  {verdict}", "", "per class:"]
        by = pair.cohort.select.by + pair.cohort.select.balance
        lines += [f"  {dict(zip(by, key))}: {n}" for key, n in sorted(cells.items(), key=str)] or ["  (the cohort draws on no class)"]
        lines += ["", common.table(["target", "metric", "n", "counts"],
                                   [[t, s["metric"], s["n"], s["counts"]] for t, s in stats.items()])]
        doc = {"pair": target, "counts": result.counts, "draw": verdict, "classes": {str(k): v for k, v in cells.items()}, "targets": stats}
        slug = target.replace("@", "_").replace(":", "_")
        return Result("\n".join(lines), {f"{slug}.json": json.dumps(doc, indent=1) + "\n"})
