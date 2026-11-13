"""`medomni studio testdata <encoder>`: write an encoder's test inputs and PROVENANCE.md into its `testdata/` (v0.2's
22 `prepare_testdata.py`, as one tool over Core's dummy-file writer). Every file is synthetic, from a seed: a healthy
input that conforms to the encoder's family, and an empty file that must degrade. `--strip-checkpoint` keeps a
checkpoint's model tensors only (v0.2's 2 `strip_checkpoint.py`).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from .. import common
from ..tools import Assets, Result

PROVENANCE = """# Fixture provenance

Synthetic fixtures written by `medomni studio testdata {eid}` from seed {seed}; no patient data. Licensed Apache-2.0 with this repository.
"""


class Testdata(Assets):
    name = "testdata"
    summary = "write an encoder's test inputs and PROVENANCE.md into its testdata/"
    target = "encoder"
    target_help = "<family>__<encoder>"

    def options(self, p) -> None:
        p.add_argument("--seed", type=int, default=0)
        p.add_argument("--level", choices=("format", "physiology"), default="format")
        p.add_argument("--force", action="store_true", help="overwrite existing test inputs")
        p.add_argument("--strip-checkpoint", nargs=2, metavar=("IN", "OUT"), help="keep only a checkpoint's model tensors")

    def folder(self, target, a, ctx) -> Path:
        return Path(a.out) if a.out else common.encoder_dir(target) / "testdata"

    def make(self, target, a, ctx) -> Result:
        if a.strip_checkpoint:
            return self._strip(*a.strip_checkpoint)
        from medomni.core import families
        from medomni.core.families.dummy import make_dummy

        edir = common.encoder_dir(target)
        family = families.get(yaml.safe_load((edir / "card.yaml").read_text(encoding="utf-8"))["family"])
        out = self.folder(target, a, ctx)
        if not a.force and any(out.glob("input*")):
            return Result(f"{target}: {out} already holds test inputs; pass --force to overwrite", code=1)
        with tempfile.TemporaryDirectory(prefix="medomni-testdata-") as tmp:
            made = make_dummy(family, a.seed, tmp, "input", level=a.level)
            files = {p.name: p.read_bytes() for p in Path(tmp).iterdir()}
        ext = "".join(made.suffixes[-1:])
        files[f"input-empty{ext}"] = b""
        files["PROVENANCE.md"] = PROVENANCE.format(eid=target, seed=a.seed)
        note = f"{target}: run `medomni perception check --freeze {edir}` to write expected.json"
        return Result(note, files)

    def _strip(self, src: str, dst: str) -> Result:
        import torch

        checkpoint = torch.load(src, map_location="cpu", weights_only=False)
        state = dict(checkpoint["model"])
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        torch.save(state, dst)
        return Result(f"kept {len(state)} model tensors of epoch {checkpoint.get('epoch')}")
