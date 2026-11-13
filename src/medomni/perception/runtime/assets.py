"""Fetch an encoder's pinned assets on the host, or verify them in a Docker build (R-117).

    python assets.py --folder perception/encoders/<family>/<encoder>      # fetch what is missing, then verify
    python assets.py --verify-only                                        # in a build: verify only

`<folder>/assets.json` lists every file. Each item has:

- `path`: where the file goes, relative to the assets directory (`<folder>/assets`, or `--directory`);
- `sha256`: the pinned digest; a file that does not match fails the step;
- a source: `url`, or a Hugging Face file as `repo`, `file`, `revision` and `type` (`model` or `dataset`);
- optionally `unpack`: an archive to extract, as `{"glob": "<top folder pattern>", "to": "<folder>",
  "check": "<file that must exist inside>"}`;
- optionally `weights: true`: this file is the checkpoint the card pins (`weights.sha256`); the encoder tests
  check that the two agree.

Standard library only, so it runs before any dependency is installed. `--folder` defaults to this file's folder,
which is where a Dockerfile copies it with the manifest.
"""
import argparse
import hashlib
import json
import shutil
import tarfile
import urllib.request
from pathlib import Path


class AssetError(RuntimeError):
    pass


def manifest(folder):
    items = json.loads((Path(folder) / "assets.json").read_text(encoding="utf-8"))
    if not isinstance(items, list) or not items:
        raise AssetError(f"{folder}/assets.json: expected a non-empty list of files")
    for item in items:
        if not {"path", "sha256"} <= set(item) or not ("url" in item or "repo" in item):
            raise AssetError(f"{folder}/assets.json: {item.get('path')}: needs path, sha256 and url or repo")
    return items


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(item, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if "repo" in item:
        from huggingface_hub import hf_hub_download

        source = hf_hub_download(item["repo"], item["file"], revision=item["revision"],
                                 repo_type=item.get("type", "model"))
        shutil.copyfile(source, target)
    else:
        urllib.request.urlretrieve(item["url"], target)


def unpack(item, directory):
    spec = item["unpack"]
    dest = directory / spec["to"]
    shutil.rmtree(dest, ignore_errors=True)
    with tarfile.open(directory / item["path"]) as bundle:
        bundle.extractall(directory)
    next(directory.glob(spec["glob"])).rename(dest)


def run(folder, directory=None, verify_only=False):
    folder = Path(folder)
    directory = Path(directory) if directory else folder / "assets"
    items = manifest(folder)
    for item in items:
        target = directory / item["path"]
        if not verify_only and not target.exists():
            fetch(item, target)
            if "unpack" in item:
                unpack(item, directory)
        if not target.is_file() or digest(target) != item["sha256"]:
            raise AssetError(f"missing or mismatched asset: {target}; run assets.py --folder {folder}")
        if "unpack" in item and not (directory / item["unpack"]["to"] / item["unpack"]["check"]).is_file():
            raise AssetError(f"{item['path']} was not unpacked into {directory / item['unpack']['to']}")
    return len(items)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--folder", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--directory", type=Path, help="the assets directory (default: <folder>/assets)")
    a = parser.parse_args(argv)
    print(f"Verified {run(a.folder, a.directory, a.verify_only)} assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
