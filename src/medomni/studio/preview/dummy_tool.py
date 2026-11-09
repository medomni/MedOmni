"""`medomni studio dummy`: the dummy-data tool of the preview kind, over `studio/dummy.py`."""
from __future__ import annotations

from ..tools import Preview, Result


class Dummy(Preview):
    name = "dummy"
    summary = "make a dummy raw folder for a dataset package"
    target = "dataset"

    def options(self, p) -> None:
        p.add_argument("--subjects", type=int, default=10)
        p.add_argument("--seed", type=int, default=0)
        p.add_argument("--level", choices=("physiology", "format"), default="physiology")

    def make(self, target, a, ctx) -> Result:
        from pathlib import Path

        from ..dummy import run

        if not a.out:
            return Result("medomni studio dummy: --out is required", code=2)
        a.dataset, a.out = target, Path(a.out)
        return Result(code=run(a))
