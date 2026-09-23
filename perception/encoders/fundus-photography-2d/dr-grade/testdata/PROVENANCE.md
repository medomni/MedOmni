# Fixture

All three files are **authored**, and hold no patient data. They are synthetic
DICOMs written with pydicom: eight-bit, Ophthalmic Photography 8 Bit Image,
explicit VR little endian, uncompressed.

`input.dcm` is a 512x512 colour frame built to look like a fundus photograph
rather than noise — a circular field on black, a bright disc off to one side, a
darker macula, nine vessel-shaped tracks radiating from the disc, and the
red-dominant balance a retina has — so the response is the model reading
structure. The frozen score is a regression baseline; it is not a clinical
grade, and nothing here says a real grader would agree with it.

`input-infrared.dcm` is the same frame as one plane. Infrared is a different
acquisition, and the family declares it as a separate role, so this encoder
degrades rather than grading it. The family decoder reads it happily — the
refusal is this encoder's.

`input-small.dcm` is the same frame at 128x128, below the 224 the model crops
to. Enlarging it would invent detail the camera never captured, so it degrades.

SHA-256:

- `input.dcm`: `7b07c67af65496790f96f9a7345d5fea6d2b7ae0df3a9ce80bce5aa001a6774e`
- `input-infrared.dcm`: `0810c9f65b1e159f680ba0a749bb455f42d3f9c03c5dfbde4f99cf75500c0abb`
- `input-small.dcm`: `46d41923f541364dbe15a8e1b33ed511d9dcc272bf74256e88cfcca84c973cb0`

## Real inference

No fixture derived from real data is committed here: the family's samples come
from AI-READI, whose agreement keeps them out of Git. Real inference is
verified by `registry.py family-test`, which runs the five pinned
`MedOmni/family-samples` photographs — Topcon Maestro2 480x640 JPEG-2000
frames — through the built image with Docker networking disabled.

All five pass, and the scores are 0.118, 0.049, 0.264, -0.173 and 0.643:
four round to grade 0 and one to grade 1. A screening cohort should look like
that, so the numbers are consistent rather than surprising — which is not the
same as measured. One score sits just below the scale, which exercises the
clamping path on real data; the card records both.
