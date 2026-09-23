"""Fetch MIRAGE's wrapper source and Base weights into the image, verified by digest.

Standard library only, so it runs before any dependency is installed. A file
whose sha256 does not match the card is deleted and the build fails: an image
whose card describes other weights is worse than no image.

The weights come from the Hugging Face repository the authors publish them in,
pinned by commit, not by tag: a tag can move, and a commit cannot.
"""
import hashlib
import pathlib
import urllib.request

SOURCE_REV = "c73997411485944cdedfc8de44d4202a6af8ca67"     # card.source.rev
SOURCE_DIR = pathlib.Path("/opt/mirage")
WEIGHTS_DIR = pathlib.Path("/opt/weights")

SOURCE = "https://raw.githubusercontent.com/j-morano/MIRAGE"
SOURCE_FILES = {
    # The wrapper is imported by the adapter: it defines the architecture the
    # checkpoint describes. It is used as published, on the pinned revision.
    "hf/mirage_hf.py": "07fa63e2766b67dbc0c07f0d9d29db1562f707425ef2fbf90a688f62a94e6ede",
    # The upstream README claims CC BY 4.0 and says the model may be used
    # commercially; this file, and the Hugging Face model card, both say
    # CC BY-NC-ND 4.0. The file travels into the image so the terms the
    # authors actually shipped are readable beside the weights they govern.
    "LICENSE": "38762e3777f4ec00a6f769062a7c3f704fb78ce08303ecff88558da4c49cf9ea",
}

WEIGHTS_REPO = "j-morano/MIRAGE-Base"
WEIGHTS_REV = "d8bdbf167604c6ca021820f268d3edc96851cf35"
WEIGHTS_FILES = {
    "model.safetensors": "bdb3ad174fd8106f32e692446479966ebf095fa8f9a523f9b29185ed0136c339",
    "config.json": "55ece6b8cac31a879543d13e8e2ae95a0174945a198b0187176dc337488ddf28",
}


def download(url, target, expected, timeout=1800):
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=timeout) as response:
        with open(target, "wb") as out:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                digest.update(chunk)
                out.write(chunk)
    got = digest.hexdigest()
    if expected is not None and got != expected:
        target.unlink(missing_ok=True)
        raise SystemExit(f"{url}\n  expected sha256 {expected}\n  got      sha256 {got}")
    print(f"verified {target} ({target.stat().st_size} bytes)")


def main():
    for name, sha in SOURCE_FILES.items():
        download(f"{SOURCE}/{SOURCE_REV}/{name}", SOURCE_DIR / pathlib.Path(name).name,
                 sha, timeout=120)
    for name, sha in WEIGHTS_FILES.items():
        download(f"https://huggingface.co/{WEIGHTS_REPO}/resolve/{WEIGHTS_REV}/{name}",
                 WEIGHTS_DIR / name, sha)
    print(f"source revision {SOURCE_REV}; weights {WEIGHTS_REPO}@{WEIGHTS_REV}")


if __name__ == "__main__":
    main()
