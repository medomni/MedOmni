"""`medomni studio release-check`: whether the release tree may be published (s4 part 4; R-158 D1, R-161).

It reads three things, and any conflict fails the check:

- Encoder cards. Every card states a licence (Core's model card contract requires one), and every built image carries
  the same licence as its `org.medomni.license` label. Restricted licences ship like the rest, stated on both (D1).
- Dataset policies. Each file under a dataset package is a kind its `publish` rules name, and that kind is allowed.
  A package holds schema files (dataset.yaml, codes.csv, evidence.yaml, policy.yaml, vocabularies, hooks,
  converters), templates (template.yaml, arm files) and recipes (cohorts, labels.yaml). Any other file is refused,
  since the publish rules can't place it.
- Data files: signals, images and arrays. Each sits in a folder, or the folder above it, with a PROVENANCE file that
  states a licence. Site images under `docs/` aren't data.

The pinned task sets' version-bump check (`medomni studio task check --release`) runs as part of it. The release tree
is the tracked files less `internal_docs/`.
"""
from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path, PurePosixPath

from ..tools import Result, Review

PRIVATE = ("internal_docs/",)
LICENSE_LABEL = "org.medomni.license"  # set by `medomni perception check`'s build (registry/build.py)
KINDS = {  # file patterns under a dataset package -> the publish rule that covers them
    "schema": ("dataset.yaml", "codes.csv", "evidence.yaml", "policy.yaml", "vocab.yaml", "*.md", "hooks/*.py",
               "converters/*.py"),
    "templates": ("tasks/*/template.yaml", "tasks/*/arms/*.yaml"),
    "recipes": ("labels.yaml", "tasks/*/cohorts/*.yaml"),
}
DATA = {".edf", ".bdf", ".dat", ".hea", ".atr", ".dcm", ".h5", ".hdf5", ".npz", ".npy", ".parquet", ".vital", ".mat",
        ".pt", ".pth", ".pkl", ".bin", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".nii", ".gz", ".zst"}
NOT_DATA = ("docs/",)
PROVENANCE = ("PROVENANCE.md", "PROVENANCE.json")
STATES_LICENSE = re.compile(r"(?i)\blicen[cs](e|ed|es)\b")


def release_files(repo: Path) -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=repo, capture_output=True, text=True, check=True).stdout
    return [f for f in out.splitlines() if f and not f.startswith(PRIVATE)]


def kind_of(rel: str) -> str | None:
    """The publish kind of a file, by its path inside its dataset package; None when no kind covers it."""
    return next((k for k, pats in KINDS.items() if any(fnmatch.fnmatchcase(rel, p) for p in pats)), None)


def package_problems(repo: Path, files: list[str]) -> list[str]:
    from medomni.core.contracts import ContractError, DatasetPolicy, load

    out, by_ds = [], {}
    for f in files:
        parts = f.split("/")
        if len(parts) > 3 and parts[:2] == ["studio", "datasets"]:
            by_ds.setdefault(parts[2], []).append("/".join(parts[3:]))
    for ds, rels in sorted(by_ds.items()):
        try:
            policy = load(repo / "studio/datasets" / ds / "policy.yaml", DatasetPolicy)
        except (ContractError, OSError) as e:
            out.append(f"dataset {ds}: no readable policy.yaml, so none of its files may ship: {str(e).splitlines()[0]}")
            continue
        publish = policy.publish.model_dump(by_alias=True)
        for rel in sorted(rels):
            kind = kind_of(rel)
            if kind is None:
                out.append(f"dataset {ds}: {rel} is not a schema, template or recipe file; the publish rules can't place it")
            elif publish[kind] != "allow":
                cond = policy.route_conditions.get(kind)
                out.append(f"dataset {ds}: {rel} is a {kind} file, and the policy says {publish[kind]}"
                           + (f" ({cond})" if cond else ""))
    return out


def data_problems(repo: Path, files: list[str]) -> list[str]:
    out, checked = [], {}
    for f in files:
        p = PurePosixPath(f)
        if p.suffix.lower() not in DATA or f.startswith(NOT_DATA) or p.name in PROVENANCE:
            continue
        folder = p.parent
        if folder not in checked:
            found = next((repo / d / n for d in (folder, folder.parent) for n in PROVENANCE if (repo / d / n).is_file()), None)
            if found is None:
                checked[folder] = f"{folder}: data files with no PROVENANCE file beside them"
            elif not STATES_LICENSE.search(found.read_text(encoding="utf-8", errors="replace")):
                checked[folder] = f"{folder}: {found.relative_to(repo).as_posix()} states no licence"
            else:
                checked[folder] = None
        if checked[folder] and checked[folder] not in out:
            out.append(checked[folder])
    return out


def card_problems(repo: Path, files: list[str], labels_of=None) -> list[str]:
    """Each card's licence, and each runnable encoder's image label against it. `labels_of(image)` gives the image's
    labels, or None when it isn't on this machine; without it, images aren't read."""
    import yaml

    out = []
    for f in sorted(f for f in files if fnmatch.fnmatchcase(f, "perception/encoders/*/*/card.yaml")):
        edir = (repo / f).parent
        eid = f"{edir.parent.name}__{edir.name}"
        lic = str((yaml.safe_load((repo / f).read_text(encoding="utf-8")) or {}).get("license") or "").strip()
        if not lic:
            out.append(f"{eid}: the card states no licence")
            continue
        if labels_of is None or not (edir / "adapter.py").is_file():
            continue
        image = f"ghcr.io/medomni/{eid}:dev"  # the registry's own tag format
        labels = labels_of(image)
        if labels is None:
            out.append(f"{eid}: {image} is not on this machine, so its licence label can't be read")
        elif (labels or {}).get(LICENSE_LABEL) is None:
            out.append(f"{eid}: {image} has no {LICENSE_LABEL} label; rebuild it with `medomni perception check`")
        elif labels[LICENSE_LABEL] != lic:
            out.append(f"{eid}: {image} is labelled {labels[LICENSE_LABEL]!r}, the card says {lic!r}")
    return out


def _docker_labels(image: str):
    """An image's labels, or None when it isn't on this machine (or there's no Docker)."""
    import json

    try:
        out = subprocess.run(["docker", "image", "inspect", "--format", "{{json .Config.Labels}}", image],
                             capture_output=True, text=True)
    except OSError:
        return None
    return json.loads(out.stdout.strip() or "null") or {} if out.returncode == 0 else None


def problems(repo: Path, images: bool = True) -> dict[str, list[str]]:
    from medomni.studio.task import _release

    files = release_files(repo)
    return {"encoder licences": card_problems(repo, files, _docker_labels if images else None),
            "dataset publish rules": package_problems(repo, files),
            "data files": data_problems(repo, files),
            "task set versions": _release()}


class ReleaseCheck(Review):
    name = "release-check"
    summary = "check that the release tree may be published: licences, publish rules, data provenance"

    def options(self, p) -> None:
        p.add_argument("--no-images", action="store_true", help="don't read the images' licence labels (no Docker)")

    def make(self, target, a, ctx) -> Result:
        from medomni.core import plugins

        repo = plugins.find_repo()
        if repo is None:
            return Result("release-check reads the release tree: run it inside the repository", code=2)
        found = problems(repo, images=not a.no_images)
        lines = []
        for part, ps in found.items():
            lines.append(f"{part}: {'ok' if not ps else f'{len(ps)} problem(s)'}")
            lines += [f"  {p}" for p in ps]
        n = sum(len(ps) for ps in found.values())
        lines.append("release-check: " + ("ok" if not n else f"{n} problem(s)"))
        return Result("\n".join(lines), code=1 if n else 0)
