"""`medomni studio encoder-demo <encoder>`: run an encoder on one sample and print its evidence (v0.2's 66 `demo.py`
and `container.py`'s `show_card` / `tour`). Over Perception's adapter interface: Docker by default, or in this
environment with `--local`, through `medomni.perception.runtime.serve`, the one call path every encoder has."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

from .. import common
from ..tools import Assets, Result, ToolError


def show_card(card: dict) -> list[str]:
    lines = [f"{card.get('id')}   family {card.get('family')}   modality {card.get('modality')}"]
    for field in ("summary", "intended_use"):
        if card.get(field):
            lines += [f"{field}:", "  " + " ".join(str(card[field]).split())]
    if card.get("limits"):
        lines.append("limits:")
        lines += ["  - " + " ".join(str(x).split()) for x in card["limits"]]
    lines.append("outputs:")
    for block in card.get("outputs") or []:
        lines.append(f"  kind {block.get('kind')}" + (f", scale {block['scale']}" if block.get("scale") else ""))
    return lines


def show_response(name: str, r: dict, top_n: int = 6) -> list[str]:
    lines = [f"--- {name}: healthy {r.get('healthy')}"]
    for out in r.get("outputs") or []:
        lines.append(f"  {out.get('kind')}:")
        items = out.get("items") or out.get("labels") or []
        lines += [f"    {json.dumps(i)}" for i in items[:top_n]]
        if len(items) > top_n:
            lines.append(f"    ... +{len(items) - top_n} more")
        if not items and out.get("text"):
            lines.append(f"    {str(out['text'])[:200]}")
    if r.get("notes"):
        lines += ["  notes:"] + [f"    {n}" for n in r["notes"]]
    return lines


def encode_local(edir: Path, family: str, sample: str, options: dict) -> dict:
    env = {**os.environ, "CARD_PATH": str(edir / "card.yaml"), "ADAPTER_PATH": str(edir / "adapter.py")}
    p = subprocess.run([sys.executable, "-m", "medomni.perception.runtime.serve", "encode", "--family", family, "--path", sample,
                        "--data-root", str(edir / "testdata"), "--options-json", json.dumps(options)],
                       env=env, capture_output=True, text=True)
    return _json_or_refuse(p, sample)


def encode_docker(eid: str, edir: Path, family: str, sample: str, options: dict, image_tag: str) -> dict:
    tag = f"ghcr.io/medomni/{eid}:{image_tag}"
    p = subprocess.run(["docker", "run", "--rm", "--network", "none", "-v", f"{edir / 'testdata'}:/data:ro", tag,
                        "python", "-m", "medomni.perception.runtime.serve", "encode", "--family", family, "--path", sample,
                        "--data-root", "/data", "--options-json", json.dumps(options)], capture_output=True, text=True)
    return _json_or_refuse(p, sample)


def _json_or_refuse(p, sample: str) -> dict:
    try:
        return json.loads(p.stdout)
    except ValueError:
        raise ToolError(f"{sample}: encoder gave no response: {p.stderr[-400:]}") from None


class EncoderDemo(Assets):
    name = "encoder-demo"
    summary = "run an encoder on one sample and print its evidence"
    target = "encoder"
    target_help = "<family>__<encoder>"

    def options(self, p) -> None:
        p.add_argument("--local", action="store_true", help="in this Python environment, not its Docker image")
        p.add_argument("--sample", help="a file under the encoder's testdata/ (default: the first input*)")
        p.add_argument("--tag", default="dev", help="image tag (default: dev)")
        p.add_argument("--top", type=int, default=6, help="output items to show")

    def make(self, target, a, ctx) -> Result:
        edir = common.encoder_dir(target)
        card = yaml.safe_load((edir / "card.yaml").read_text(encoding="utf-8"))
        samples = [a.sample] if a.sample else sorted(p.name for p in (edir / "testdata").glob("input*") if p.is_file() and p.stat().st_size)[:1]
        if not samples:
            return Result(f"{target}: no sample to encode; write testdata/ with `medomni studio testdata {target}`", code=1)
        lines = show_card(card)
        for name in samples:
            options = _family_options(edir, name)
            r = encode_local(edir, card["family"], name, options) if a.local else \
                encode_docker(target, edir, card["family"], name, options, a.tag)
            if "error" in r:
                return Result("\n".join(lines) + f"\n{name}: refused: {r['error']}", code=1)
            lines += show_response(name, r, a.top)
        return Result("\n".join(lines))


def _family_options(edir: Path, name: str) -> dict:
    p = edir / "family-test.json"
    if not p.is_file():
        return {}
    cfg = json.loads(p.read_text(encoding="utf-8"))
    default, sample = cfg.get("default", {}), cfg.get("samples", {}).get(name, {})
    return {**default.get("options", default), **sample.get("options", sample)}
