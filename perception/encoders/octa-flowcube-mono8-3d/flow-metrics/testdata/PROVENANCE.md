# Fixture

All three files are **authored**, and hold no patient data. They are synthetic
DICOMs written with pydicom: 200x256 frames, eight-bit, Ophthalmic Tomography
Image, explicit VR little endian, uncompressed.

`input.dcm` holds six flow frames built to look like an angiogram rather than
noise: 46 vessel-shaped columns of raised signal confined to a superficial
band around axial row 55, over a low background, with seeded noise so the file
is reproducible. It is built so that every measure has something to find — the
projection binarises into a network with both area and length, and the depth
centroid sits above the middle of the cube rather than at its centre.

`input-blank.dcm` is three frames of zeros; `input-single.dcm` holds one
frame. Both are authored rejection cases: a cube of nothing has no flow to
measure, and a stack of one is a different family, not a small cube.

SHA-256:

- `input.dcm`: `da1e4eedb480aba1d02c9e4949c9cf35527392db785085c8171bdd99ec62a4eb`
- `input-blank.dcm`: `417e25ba967366e171a59b50ae7c0ac09b650c6be612da2b7e3b56a5db6b0b44`
- `input-single.dcm`: `221a3e0c2f849700a5064421144b4f5b5ec3691a9176481ae2acc32d611a856e`

## Method check

Otsu's threshold and the vessel area density were cross-checked against
scikit-image's own `threshold_otsu` on the three published family samples and
agreed exactly (thresholds 3, 4, 4; densities to four decimals). A hand-written
Zhang-Suen thinning agreed with `skeletonize` to within four percent, which is
why the adapter calls scikit-image rather than carrying its own morphology.

## Real inference

No fixture derived from real data is committed here: the family's samples come
from AI-READI, whose agreement keeps them out of Git. Real inference is
verified by `registry.py family-test`, which runs the three pinned
`MedOmni/family-samples` cubes — Spectralis 20x20 mm acquisitions of 13, 20 and
26 B-scans at 496x512, JPEG-lossless — through the built image with Docker
networking disabled.
