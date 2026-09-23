# Fixture

All three files are **authored**, and hold no patient data. They are synthetic
DICOMs written with pydicom: 248x256 B-scans, eight-bit, Ophthalmic Tomography
Image, explicit VR little endian, uncompressed.

`input.dcm` holds eight B-scans built to look like retina rather than noise:
five layer-shaped intensity bands over a foveal depression, shifted slightly
from scan to scan so the stack is not eight copies of one image, plus speckle
from a seeded generator so the file is reproducible. Values span 0 to 214,
mean 38.24. The frozen response records what this model says about it; it is a
regression baseline, and an embedding has no clinical ground truth to check it
against.

`input-blank.dcm` is four B-scans of zeros. Every scan is blank, so the family
decoder degrades it rather than letting the model embed nothing. It is the
shape two published `octa-enface-slab-mono8-2d` samples arrive in.

`input-single.dcm` holds one B-scan. This family is a stack, and a single
frame is a different family, so it degrades. It is an authored rejection case.

SHA-256:

- `input.dcm`: `e344f4e4d5a7ee42ef0b9e62ef22690b7673bcc79762698fa4c3695498675db8`
- `input-blank.dcm`: `a96f9125b9a22f64594cceea2b482423c371e7b1d533fcc765101912cf0419e8`
- `input-single.dcm`: `7c53e16090c546e886bbcfe6511ff07dc09634ba3c227fc7d440aad3a20be542`

## Real inference

No fixture derived from real data is committed here: the family's samples come
from AI-READI, whose agreement keeps them out of Git. Real inference is
verified by `registry.py family-test`, which runs the three pinned
`MedOmni/family-samples` volumes — Spectralis 20x20 macular acquisitions of
13, 20 and 26 B-scans at 496x512, JPEG-lossless — through the built image with
Docker networking disabled.

Those three samples come from the OCTA acquisition's structural channel
(`..._octa_oct_...`) rather than a dedicated raster volume series, which is a
question open with Data & Task. It does not change what this encoder reads:
they are macular OCT B-scans, and they conform to the family's declaration.
