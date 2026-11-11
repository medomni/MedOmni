"""`medomni perception`: pull and run encoders, the gateway, and the contributor's encoder commands.

    medomni perception pull [<family-or-encoder> ...]   pull encoder images from ghcr.io/medomni
    medomni perception up --data-root <dir>             start the gateway on 127.0.0.1:8000
    medomni perception new <family>/<encoder>           write an encoder folder to fill in
    medomni perception check <encoder-folder>           card, image build, testdata, real samples (R-122)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="medomni perception", description="Pull and run encoders; the gateway.")
    sub = ap.add_subparsers(dest="cmd", metavar="<command>")
    p = sub.add_parser("pull", help="pull encoder images from ghcr.io/medomni")
    p.add_argument("targets", nargs="*", metavar="<family-or-encoder>", help="default: the workspace's encoder set")
    p.add_argument("--tag", default="dev", help="image tag (default: dev)")
    u = sub.add_parser("up", help="start the gateway on the pulled encoders")
    u.add_argument("--data-root", required=True, help="host folder mounted read-only at /data")
    u.add_argument("--host", default="127.0.0.1")
    u.add_argument("--port", type=int, default=8000)
    u.add_argument("--max-live", type=int, dest="max_live_containers", help="how many containers may run at once")
    n = sub.add_parser("new", help="write an encoder folder to fill in, with an empty testdata/")
    n.add_argument("encoder", metavar="<family>/<encoder>")
    c = sub.add_parser("check", help="check an encoder folder: card, image build, testdata, real samples")
    c.add_argument("folder", type=Path, metavar="<encoder-folder>")
    c.add_argument("--samples", type=Path, help="a folder of family samples, one sub-folder per family")
    c.add_argument("--freeze", action="store_true", help="write testdata/expected.json instead of comparing")
    c.add_argument("--tol", type=float, help="number tolerance (default 1e-3)")
    c.add_argument("--record", action="store_true", help="write a passing encoder into perception/deployed.yaml, the record the perception service starts images from")
    return ap


def _targets(names):
    """Encoder ids for pull: each name is an encoder id or a family id; none means the workspace's encoder set."""
    from . import registry

    dirs = registry.encoder_dirs()
    ids = [registry.encoder_id(d) for d in dirs]
    if not names:
        from medomni.core import workspace

        names = list(workspace.load().deployment.get("encoders") or [])
        if not names:
            raise registry.RegistryError("no encoders named, and the workspace deployment lists none")
    out = []
    for name in names:
        found = [i for i in ids if i == name or i.split("__", 1)[0] == name]
        if not found:
            raise registry.RegistryError(f"no encoder or family '{name}'")
        out += [i for i in found if i not in out]
    return out


def cmd_pull(a) -> int:
    from . import registry

    failed = 0
    for eid in _targets(a.targets):
        image = registry.tag(eid, a.tag)
        if subprocess.call(["docker", "pull", image]) != 0:
            failed += 1
            print(f"[{eid}] pull failed: {image}", file=sys.stderr)
    return 1 if failed else 0


def cmd_up(a) -> int:
    from .gateway import app, config

    try:
        deployment = config.from_workspace(overrides={"data_root": a.data_root,
                                                      "max_live_containers": a.max_live_containers})
    except config.ConfigError as exc:
        print(f"deployment config: {exc}", file=sys.stderr)
        return 2
    app.serve(deployment, host=a.host, port=a.port)
    return 0


def cmd_new(a) -> int:
    from . import registry
    from .scaffold import write

    if a.encoder.count("/") != 1:
        print("give <family>/<encoder>", file=sys.stderr)
        return 2
    family, name = a.encoder.split("/")
    target = registry.encoders_root() / family / name
    if target.exists():
        print(f"{target} already exists", file=sys.stderr)
        return 2
    from medomni.core import families

    families.get(family)  # an unknown family is an error, not a folder to fill in
    for p in write(target, family, name):
        print(f"wrote {p}")
    return 0


def cmd_check(a) -> int:
    from .registry.check import TOL, check

    if a.record and a.freeze:
        print("--record and --freeze can't be combined: a frozen expected.json is not a check", file=sys.stderr)
        return 2
    return check(a.folder, samples_root=a.samples, do_freeze=a.freeze, tol=a.tol if a.tol is not None else TOL, record=a.record)


def group(argv: list[str]) -> int:
    ap = _parser()
    a = ap.parse_args(argv)
    if a.cmd is None:
        ap.print_help()
        return 0
    from . import registry
    from medomni.core.families import FamilyError

    try:
        return {"pull": cmd_pull, "up": cmd_up, "new": cmd_new, "check": cmd_check}[a.cmd](a)
    except (registry.RegistryError, FamilyError) as exc:
        print(f"medomni perception {a.cmd}: {exc}", file=sys.stderr)
        return 2
