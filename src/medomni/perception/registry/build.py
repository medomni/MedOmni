"""Encoder image builds. An image gets the shared runtime, Core's families module and its own folder, at their
repository paths. The build context is staged per encoder in `build/docker-context/<id>/` (gitignored): hard links
to the paths its `Dockerfile.dockerignore` allows, weights included. Staging works with Docker's legacy builder,
which reads no per-Dockerfile ignore file and would otherwise upload the whole repository; hard links cost no disk.

The build key is the sha256 over the files an image is built from (git's view: tracked plus untracked, minus
.gitignore, so downloaded weights are left out while their pins are in). Same commit, same key on any machine; a
runtime change stales every encoder.
"""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from . import LABEL_NS, RegistryError, encoder_id, repo_root, tag

# What every image copies besides its own folder (the Dockerfiles copy exactly these)
SHARED = ("src/medomni/__init__.py", "src/medomni/core", "src/medomni/perception/__init__.py",
          "src/medomni/perception/runtime", "core/families")
_SKIP_PARTS = {"__pycache__", ".pytest_cache"}


def context_files(edir, repo=None):
    repo = Path(repo or repo_root(edir))
    files = []
    for rel in (*SHARED, Path(edir).resolve().relative_to(repo).as_posix()):
        base = repo / rel
        if base.is_file():
            files.append(base)
            continue
        listed = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=base,
                                capture_output=True, text=True)
        paths = ([base / line for line in listed.stdout.splitlines()] if listed.returncode == 0
                 else list(base.rglob("*")))
        files += sorted(p for p in paths
                        if p.is_file() and not _SKIP_PARTS & set(p.parts) and p.suffix != ".pyc")
    return files


def build_key(edir, repo=None):
    repo = Path(repo or repo_root(edir))
    digest = hashlib.sha256()
    for path in context_files(edir, repo):
        digest.update(path.relative_to(repo).as_posix().encode() + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return "sha256:" + digest.hexdigest()


def git_rev(paths, repo):
    """The HEAD commit, or 'dev-dirty' when any of the paths has uncommitted changes."""
    rel = [str(Path(p).resolve().relative_to(repo)) for p in paths]
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *rel], cwd=repo,
                           capture_output=True, text=True).stdout.strip()
    return "dev-dirty" if dirty else head


def allowed(edir) -> list[str]:
    """The repository paths an encoder's image is built from: the `!` lines of its `Dockerfile.dockerignore`."""
    ignore = Path(edir) / "Dockerfile.dockerignore"
    if not ignore.is_file():
        raise RegistryError(f"{encoder_id(edir)}: no Dockerfile.dockerignore")
    return [line[1:].strip() for line in ignore.read_text(encoding="utf-8").splitlines() if line.startswith("!")]


def stage(edir, repo=None) -> Path:
    """Hard-link the allowed paths and the Dockerfile into `build/docker-context/<id>/`; returns that folder."""
    edir = Path(edir).resolve()
    repo = Path(repo or repo_root(edir)).resolve()
    dst = repo / "build/docker-context" / encoder_id(edir)
    if dst.exists():
        shutil.rmtree(dst)
    for rel in (*allowed(edir), edir.relative_to(repo).as_posix() + "/Dockerfile"):
        src = repo / rel
        if not src.exists():
            raise RegistryError(f"{encoder_id(edir)}: {rel} is allowed in the build but missing")
        files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file()
                                                    and not _SKIP_PARTS & set(p.parts) and p.suffix != ".pyc")
        for f in files:
            target = dst / f.relative_to(repo)
            if target.exists():  # allowed twice, e.g. a folder and a file inside it
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(f, target)
            except OSError:  # another file system: copy
                shutil.copy2(f, target)
    return dst


def command(edir, repo=None, image_tag="dev", context=None):
    """The docker build command for one encoder folder, over its staged context (`stage`)."""
    edir, repo = Path(edir).resolve(), Path(repo or repo_root(edir)).resolve()
    eid = encoder_id(edir)
    context = Path(context) if context else repo
    return ["docker", "build", "-t", tag(eid, image_tag),
            "--label", f"{LABEL_NS}.encoder_id={eid}",
            "--label", f"{LABEL_NS}.build_key={build_key(edir, repo)}",
            "--label", f"{LABEL_NS}.source_rev={git_rev([repo / p for p in SHARED] + [edir], repo)}",
            "-f", str(context / edir.relative_to(repo) / "Dockerfile"), str(context)]


def image_labels(image):
    out = subprocess.run(["docker", "image", "inspect", "--format", "{{json .Config.Labels}}|{{.Id}}", image],
                         capture_output=True, text=True)
    if out.returncode:
        return None, None
    labels, image_id = out.stdout.strip().rsplit("|", 1)
    return json.loads(labels) or {}, image_id


def build(edir, repo=None, image_tag="dev", log=None):
    """Build one image; returns (tag, image id). Raises RegistryError when docker is missing or the build fails."""
    if not shutil.which("docker"):
        raise RegistryError("docker not found on this machine")
    edir = Path(edir).resolve()
    if not (edir / "Dockerfile").is_file():
        raise RegistryError(f"{encoder_id(edir)}: no Dockerfile")
    context = stage(edir, repo)
    try:
        cmd = command(edir, repo, image_tag, context)
        rc = subprocess.call(cmd, stdout=log, stderr=subprocess.STDOUT if log else None)
    finally:
        shutil.rmtree(context, ignore_errors=True)
    if rc:
        raise RegistryError(f"{encoder_id(edir)}: docker build failed (exit {rc})")
    image = tag(encoder_id(edir), image_tag)
    labels, image_id = image_labels(image)
    key = next(c.split("=", 1)[1] for c in cmd if c.startswith(f"{LABEL_NS}.build_key="))
    if not image_id or (labels or {}).get(f"{LABEL_NS}.build_key") != key:
        raise RegistryError(f"{encoder_id(edir)}: the built image does not carry the expected build_key label")
    return image, image_id
