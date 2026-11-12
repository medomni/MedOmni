"""`medomni studio encoder-status`: which encoders are built and which are planned.
Built means the folder has what `medomni perception check` needs and its card passes the contract. Whether an
image exists is read from Docker only with `--images`."""
from __future__ import annotations

import subprocess

import yaml

from .. import common
from ..tools import Result, Review


def status(edir, check_images: bool) -> tuple[str, str]:
    from medomni.core.contracts import ContractError, ModelCard, load

    try:
        load(edir / "card.yaml", ModelCard)
    except ContractError as e:
        return "invalid", str(e).splitlines()[0]
    if not (edir / "adapter.py").is_file():
        return "planned", "card only: no adapter yet"
    missing = [f for f in ("Dockerfile", "testdata/expected.json") if not (edir / f).is_file()]
    if missing:
        return "planned", f"adapter, but no {', '.join(missing)}"
    if check_images and not _image_present(common.encoder_id(edir)):
        return "unbuilt", "no local image"
    return "built", "adapter, image recipe and test data present"


def _image_present(eid: str) -> bool:
    tag = f"ghcr.io/medomni/{eid}:dev"  # the registry's own tag format
    return subprocess.run(["docker", "image", "inspect", tag], capture_output=True).returncode == 0


class EncoderStatus(Review):
    name = "encoder-status"
    summary = "list which encoders are built and which are planned"

    def options(self, p) -> None:
        p.add_argument("--images", action="store_true", help="also check that the image exists locally (needs Docker)")
        p.add_argument("--ids", nargs="*", default=[], help="only these encoders")

    def make(self, target, a, ctx) -> Result:
        rows, doc, counts = [], {}, {}
        for edir in common.encoder_dirs():
            eid = common.encoder_id(edir)
            if a.ids and eid not in a.ids:
                continue
            state, reason = status(edir, a.images)
            card = yaml.safe_load((edir / "card.yaml").read_text(encoding="utf-8"))
            counts[state] = counts.get(state, 0) + 1
            rows.append([eid, card.get("family"), state, reason])
            doc[eid] = {"state": state, "reason": reason, "acceptance": card.get("acceptance")}
        text = common.table(["encoder", "family", "status", "why"], rows) + "\n\n" + \
            " · ".join(f"{k} {v}" for k, v in sorted(counts.items()))
        import json

        return Result(text, {"status.json": json.dumps(doc, indent=1, sort_keys=True) + "\n"})
