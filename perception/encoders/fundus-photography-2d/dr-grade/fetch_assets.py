"""Fetch the diabetic-retinopathy grading checkpoint, verified by digest.

Standard library only, so it runs before any dependency is installed. A file
whose sha256 does not match the card is deleted and the build fails.

The checkpoint is pinned by commit rather than by branch: a Hugging Face
repository's main can move, and a commit cannot.
"""
import hashlib
import pathlib
import urllib.request

WEIGHTS_REPO = "ClementP/FundusDRGrading-efficientnet_b0"
WEIGHTS_REV = "aa5741419b902b6f4d6607e2819a0458682e3a49"
WEIGHTS_DIR = pathlib.Path("/opt/weights")
WEIGHTS_FILES = {
    "model.safetensors": "0d9a18b0cb6c90d1f30bf2e66153b368bd7ff0bcb45b6690e8d5ce14fa19f69b",
    # The config travels with the weights: it is where the input size, crop
    # fraction, interpolation and normalisation the adapter reproduces are
    # declared, so the image carries the declaration beside what it describes.
    "config.json": "b71ee5a62c12f5af8d3bf12995037ae0b935babb50cf2b595bb94e44ea3f79d8",
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
    if got != expected:
        target.unlink(missing_ok=True)
        raise SystemExit(f"{url}\n  expected sha256 {expected}\n  got      sha256 {got}")
    print(f"verified {target} ({target.stat().st_size} bytes)")


def main():
    for name, sha in WEIGHTS_FILES.items():
        download(f"https://huggingface.co/{WEIGHTS_REPO}/resolve/{WEIGHTS_REV}/{name}",
                 WEIGHTS_DIR / name, sha)
    print(f"weights {WEIGHTS_REPO}@{WEIGHTS_REV}")


if __name__ == "__main__":
    main()
