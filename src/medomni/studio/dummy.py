"""`medomni studio dummy <dataset>`: a dummy raw folder for a dataset package, from its own `dataset.yaml` (R-70, R-71).

A thin wrapper over Core's generator (`medomni.core.families.dummy.datasets.make_dataset`), so anyone adding a dataset
package can make dummy data for it, and anyone can reproduce ours from the seed.
"""
from __future__ import annotations

import sys
from pathlib import Path

from medomni.core.testing import DATASETS as TESTING


def find_package(name: str) -> Path:
    """A path to a package folder, or a dataset name: `bench/datasets/<name>` in the repository, then Core's dummy
    packages."""
    p = Path(name)
    if (p / "dataset.yaml").is_file():
        return p
    from medomni.core import plugins

    repo = plugins.find_repo()
    for d in ([repo / "bench" / "datasets" / name] if repo else []) + [TESTING / name]:
        if (d / "dataset.yaml").is_file():
            return d
    raise FileNotFoundError(f"no dataset package '{name}' (give a folder holding dataset.yaml, or a dataset name)")


def add_parser(sub) -> None:
    p = sub.add_parser("dummy", help="make a dummy raw folder for a dataset package",
                       description="Write <out>/raw/ (a data root the package's dataset.yaml can load) and "
                                   "<out>/planted.json (the planted labels and canaries).")
    p.add_argument("dataset", help="a dataset package folder, or a dataset name")
    p.add_argument("--out", required=True, type=Path, help="the folder to write")
    p.add_argument("--subjects", type=int, default=10)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--level", choices=("physiology", "format"), default="physiology",
                   help="physiology: signals that look like the signal (default); format: values that only pass the "
                        "family checks")


def run(a) -> int:
    from medomni.core.contracts import ContractError
    from medomni.core.families.dummy.datasets import DummyError, make_dataset

    try:
        d = make_dataset(find_package(a.dataset), a.out, subjects=a.subjects, seed=a.seed, level=a.level)
    except (FileNotFoundError, ContractError, DummyError, ValueError) as e:
        print(f"medomni studio dummy: {e}", file=sys.stderr)
        return 2
    n = sum(1 for p in d.root.rglob("*") if p.is_file())
    labels = ", ".join(f"{k} {len(v['positive'])}/{len(d.subjects)}" for k, v in sorted(d.planted["labels"].items()))
    print(f"wrote {n} files for {len(d.subjects)} subjects under {d.root}")
    print(f"planted labels (positive/subjects): {labels or 'none'}; see {a.out / 'planted.json'}")
    return 0
