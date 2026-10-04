#!/usr/bin/env python3
"""Write input.png, the smoke-test image for torchxrayvision.

The image is a synthetic phantom and not a radiograph: a dark background, a
bright body, two dark lung fields, and a bright spine. It proves that the
container reads an image, runs the model, and answers with the labels its card
declares. It proves nothing about clinical behavior.

Real samples live in an access-controlled sample set, not distributed. When a published
cxr-radiograph-2d sample lands, replace input.png with it and freeze the
response again.

Standard library only, so the fixture rebuilds on any machine:

    python make_input.py

The pixels are the same every time. The compressed bytes can differ between
zlib versions, so the file is committed and not built during a build.
"""
import struct
import zlib
from pathlib import Path

SIZE = 384
BACKGROUND, BODY, LUNG, SPINE = 12, 170, 55, 225


def _ellipse(x, y, cx, cy, rx, ry):
    """How far a pixel is from the center of an ellipse. 1.0 is the edge."""
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2


def phantom(size=SIZE):
    """A chest-shaped gray image, drawn from the outside in."""
    half = size / 2
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            value = BACKGROUND
            if _ellipse(x, y, half, half, half * 0.86, half * 0.94) <= 1.0:
                value = BODY
            for side in (-1, 1):
                lung = _ellipse(x, y, half + side * half * 0.34, half * 0.98,
                                half * 0.26, half * 0.46)
                if lung <= 1.0:
                    value = int(LUNG + (BODY - LUNG) * lung)
            if abs(x - half) < size * 0.035 and _ellipse(x, y, half, half,
                                                         half * 0.86, half * 0.94) <= 1.0:
                value = SPINE
            row.append(max(0, min(255, value)))
        rows.append(row)
    return rows


def write_png(path, rows):
    """8-bit grayscale PNG, one plane, as the family protocol declares."""
    height, width = len(rows), len(rows[0])
    raw = b"".join(b"\x00" + bytes(row) for row in rows)

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n"
                     + chunk(b"IHDR", header)
                     + chunk(b"IDAT", zlib.compress(raw, 9))
                     + chunk(b"IEND", b""))


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "input.png"
    write_png(target, phantom())
    print(f"wrote {target}")
