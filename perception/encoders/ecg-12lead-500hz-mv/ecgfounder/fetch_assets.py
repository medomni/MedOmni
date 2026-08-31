#!/usr/bin/env python3
"""Put the upstream source and the weights into the image, and verify both.

Run during the build, never at run time:

    python fetch_assets.py

Every file is checked against the sha256 pinned below. Two of the three are the
sha256 the card's `source.rev` already determines; the third is the card's
`weights.sha256` itself. A build whose download does not match fails here,
rather than producing an image whose card describes something else.

net1d.py is written exactly as upstream published it. The adapter puts
/opt/ecgfounder on the path instead of copying the file next to itself, so there
is one revision of it in the image and nothing that can drift from the pin.

This is a file and not a `RUN <<EOF` heredoc in the Dockerfile on purpose. A
heredoc needs BuildKit, and the classic builder accepts one, ignores its body,
and reports success — so the assets silently do not arrive.
"""
import hashlib
import pathlib
import urllib.request

SOURCE_REV = "04edac702b61c91face519774ddcc0cd712fef23"      # card.source.rev
SOURCE_DIR = pathlib.Path("/opt/ecgfounder")
WEIGHTS_DIR = pathlib.Path("/opt/weights")

SOURCE = "https://raw.githubusercontent.com/PKUDigitalHealth/ECGFounder"
SOURCE_FILES = {
    "net1d.py": "832bf90e05e20e62db6f9c7007acf7f0b1f739938ab80fa9b2c1ad438e8da7f7",
    "tasks.txt": "7c087a0d383c7ea9ae9b818ad00a551b029334edfa5f1fbb5036bfbaa0df0c39",
}

WEIGHTS_NAME = "12_lead_ECGFounder.pth"
WEIGHTS_URL = (f"https://huggingface.co/PKUDigitalHealth/ECGFounder/resolve/main/"
               f"{WEIGHTS_NAME}")
WEIGHTS_SHA256 = "ee199f3781f4ae1f732973267f003da0a759ea12bddb0dd28a77faa60aca7997"


def download(url, target, expected, timeout=1800):
    """Stream a file to disk, and fail unless its sha256 is the pinned one."""
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=timeout) as response:
        with target.open("wb") as out:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                digest.update(chunk)
                out.write(chunk)
    got = digest.hexdigest()
    if got != expected:
        target.unlink(missing_ok=True)
        raise SystemExit(f"{target.name}: sha256\n  got      {got}\n"
                         f"  expected {expected}")
    print(f"{target.name:24s} {target.stat().st_size:>10,} bytes  sha256 verified")


def main():
    for name, sha in SOURCE_FILES.items():
        download(f"{SOURCE}/{SOURCE_REV}/{name}", SOURCE_DIR / name, sha, timeout=120)
    download(WEIGHTS_URL, WEIGHTS_DIR / WEIGHTS_NAME, WEIGHTS_SHA256)
    print(f"source revision {SOURCE_REV}")


if __name__ == "__main__":
    main()
