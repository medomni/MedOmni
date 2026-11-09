"""The encoder registry: where encoder folders are, what their cards must hold, the catalogue index, and image builds.

    from medomni.perception import registry
    registry.encoder_dirs()          # every encoder folder with a card, in order
    registry.cards.check(folder)     # (errors, warnings) for one folder
    registry.build.build(folder)     # docker build, with the repository root as context

`medomni perception check` (check.py) runs a folder's card check, image build and tests (R-122). Status views over
the whole fleet are Studio's (R-119).
"""
import re
from pathlib import Path

GHCR = "ghcr.io/medomni"
LABEL_NS = "org.medomni"
ENCODERS = "perception/encoders"
ID_RE = re.compile(r"^[a-z0-9-]+__[a-z0-9-]+$")


class RegistryError(RuntimeError):
    """No repository, no such encoder, or an encoder folder the registry cannot use."""


def repo_root(start=None) -> Path:
    from medomni.core import plugins

    repo = plugins.find_repo(start)
    if repo is None:
        raise RegistryError("no MedOmni repository found; encoder folders are read from a clone (Get started)")
    return repo


def encoders_root(repo=None) -> Path:
    return Path(repo or repo_root()) / ENCODERS


def encoder_id(edir) -> str:
    edir = Path(edir)
    return f"{edir.parent.name}__{edir.name}"


def encoder_dir(eid, root=None) -> Path:
    if not ID_RE.match(eid):
        raise RegistryError(f"'{eid}' is not <family>__<encoder>")
    d = Path(root or encoders_root()) / eid.replace("__", "/", 1)
    if not (d / "card.yaml").is_file():
        raise RegistryError(f"no such encoder: {eid}")
    return d


def encoder_dirs(ids=(), root=None) -> list[Path]:
    """Every encoder folder with a card, sorted; only `ids` when given (each must exist)."""
    root = Path(root or encoders_root())
    dirs = sorted(d for family in root.iterdir() if family.is_dir()
                  for d in family.iterdir() if d.is_dir() and (d / "card.yaml").is_file())
    if ids:
        wanted = set(ids)
        dirs = [d for d in dirs if encoder_id(d) in wanted]
        missing = wanted - {encoder_id(d) for d in dirs}
        if missing:
            raise RegistryError(f"no such encoder: {', '.join(sorted(missing))}")
    return dirs


def tag(eid, image_tag="dev") -> str:
    return f"{GHCR}/{eid}:{image_tag}"


from . import build, cards, check, index  # noqa: E402,F401  (after the names they use)

__all__ = ["GHCR", "LABEL_NS", "RegistryError", "build", "cards", "encoder_dir", "encoder_dirs", "encoder_id",
           "encoders_root", "check", "index", "repo_root", "tag"]
