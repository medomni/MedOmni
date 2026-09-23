# Fixture

All three files are **authored**, and hold no patient data. They are synthetic
DICOMs written with pydicom: 192x256 frames, eight-bit, Ophthalmic Tomography
Image, explicit VR little endian, uncompressed, each frame carrying its own
`OphthalmicFrameLocationSequence` so the geometry is read the way it is read
from a real set — a line has two endpoints, a circle has the polyline that
traces it.

`input.dcm` is a complete set: 24 radial frames and 3 circle frames. The
radial frames carry a shallow central depression standing in for the cup, and
the circle frames do not, so the two geometries are not copies of each other.
Layer-shaped bands and seeded noise make each frame retina-like rather than
constant.

`input-blank.dcm` has the same 24 + 3 composition with every pixel zero: an
authored rejection case for a set with nothing to embed.

`input-partial.dcm` holds 12 radial and 3 circle frames. The family declares
24 + 3, and a partial set is not a smaller one — the fan would be sampled at
half the angles, and an embedding averaged over it would not be comparable
with any other. It must degrade.

`input-nogeometry.dcm` is `input.dcm` with its per-frame functional groups
removed. It still conforms to the family — the decoder reads it and says the
geometry is not reported — so the refusal is this encoder's, not the family's.
It is what a set exported without reference coordinates looks like.

SHA-256:

- `input.dcm`: `95745f9056180676513ffb1b8ccfbea626825ed667ac05606e312537ca7232f4`
- `input-blank.dcm`: `4cdee3b85d1de9e7d60d98f54fa3c4b70947ac51e5b701108ffe8a836246247a`
- `input-partial.dcm`: `317f19a7b40a551c0c81f7572150bc68a4407f57fe1f423b87b85ec5329789cf`
- `input-nogeometry.dcm`: `a0401fc6773b7d5834ab17cb242de8e34969ff3e690414bcd2973e48f6805f6d`

## Real inference

No fixture derived from real data is committed here: the family's samples come
from AI-READI, whose agreement keeps them out of Git. Real inference is
verified by `registry.py family-test`, which runs the three pinned
`MedOmni/family-samples` sets — Spectralis optic-nerve-head acquisitions,
496x768, each holding exactly 24 radial and 3 circle frames — through the
built image with Docker networking disabled.
