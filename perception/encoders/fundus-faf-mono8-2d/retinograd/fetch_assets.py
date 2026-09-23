"""Fetch Retinograd-AI's source and weights into the image, verified by digest.

Standard library only, so it runs before any dependency is installed — the same
reason the ECGFounder recipe does it this way. A file whose sha256 does not
match the card is deleted and the build fails: an image whose card describes
other weights is worse than no image.
"""
import hashlib
import pathlib
import urllib.request

SOURCE_REV = "e9dd11bfe7b40ae2d00260994b811a0c987c70ec"      # card.source.rev
SOURCE_DIR = pathlib.Path("/opt/retinograd")
WEIGHTS_DIR = pathlib.Path("/opt/weights")

SOURCE = "https://raw.githubusercontent.com/Eye2Gene/retinograd-ai"
SOURCE_FILES = {
    # inference.py is the published preprocessing and head definition. The
    # adapter does not import it — it is a script, not a module — but the
    # image carries it so the pinned revision is inspectable inside the
    # container, beside the weights it describes.
    "inference.py": "41a3fc55bf87808d33782538c242ced483c48d26f0253a562a86039c5d6d1e86",
    "LICENSE": "ab8329c2f31403ce5818127038e11b738ffa302964f542a9e9587a3dbc33417a",
}

WEIGHTS_NAME = "FAF_inception_resenet_2Class_classification.pth"
WEIGHTS_URL = ("https://github.com/eye2gene/retinograd-ai/releases/download/"
               f"V0.0.1/{WEIGHTS_NAME}")
WEIGHTS_SHA256 = "5bb21bf274a0659d1a642e21fb063502ef714f2a53a83c0b7b24aabf4202a7cf"


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
    if got != expected:
        target.unlink(missing_ok=True)
        raise SystemExit(f"{url}\n  expected sha256 {expected}\n  got      sha256 {got}")
    print(f"verified {target} ({target.stat().st_size} bytes)")


def main():
    for name, sha in SOURCE_FILES.items():
        download(f"{SOURCE}/{SOURCE_REV}/{name}", SOURCE_DIR / name, sha, timeout=120)
    download(WEIGHTS_URL, WEIGHTS_DIR / WEIGHTS_NAME, WEIGHTS_SHA256)
    print(f"source revision {SOURCE_REV}")


if __name__ == "__main__":
    main()
