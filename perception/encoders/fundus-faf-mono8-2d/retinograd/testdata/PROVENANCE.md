# Fixture

All three files are **authored**, and hold no patient data. They are synthetic
DICOMs written with pydicom: 512x512, eight-bit, Ophthalmic Photography 8 Bit
Image, explicit VR little endian, uncompressed.

`input.dcm` is a greyscale frame built to look like an autofluorescence image
rather than noise — a ring of raised intensity around a darker centre, one
vessel-shaped dark band, and a fine texture — so the response is a model
reading structure and not a constant. Values span 9 to 215, mean 91.11. The
frozen response records what this model says about it; it is a regression
baseline, not a clinical ground truth, and nothing here says whether a real
grader would call this frame gradable.

`input-colour.dcm` is the same frame in three RGB planes that **disagree**
(two are shifted copies). Autofluorescence is a single-intensity measurement:
`family_alias.yaml` declares which colour containers this family accepts, RGB
is not one of them, and the family decoder degrades the file rather than
flattening three different planes into a plausible grey. It is an authored
rejection case.

`input-blank.dcm` is a conforming frame in which every pixel is zero. The
family decoder reads it — a blank frame is still a frame — so the refusal is
this encoder's: a classifier answering 0.997 for an image with no content
would be stating a fact about nothing. It must come back `healthy=false`.

SHA-256:

- `input.dcm`: `4d7e91a1f0a13de296bc371fc8259dc3fc785e4de9edff1fecd7ef3c09433a1f`
- `input-colour.dcm`: `d90b3e6d3a09bdaf6538be41c923bbe64ea326366da8d79fe5892dd26c227331`
- `input-blank.dcm`: `12658c7f95660559e9a88f01652e33e15a33c9d230423fbcd13eedb459f33d25`

## Real inference

No fixture derived from real data is committed here: the family's samples come
from AI-READI, whose agreement keeps them out of Git. Real inference is
verified by `registry.py family-test`, which runs the five pinned
`MedOmni/family-samples` DICOMs — 3288x3680 JPEG-baseline frames that the iCare
Eidon writes in a YBR_FULL_422 container — through the built image with Docker
networking disabled. That gate, not this folder, is what shows the encoder
reads the data the benchmark actually holds.

All five pass the gate: the image reads them, and every response is healthy
with two finite probabilities inside the declared vocabulary. What the model
says about them is another matter, and is recorded in the card: four of the
five come back ungradable with high confidence. Those frames are 39 to 52
percent near-black with a median intensity of 0 to 21, so the likeliest reason
is that ultra-widefield Eidon exposure is not what Retinograd-AI was trained
on. Nothing here settles that, which is why reliability stays `unmeasured`.
