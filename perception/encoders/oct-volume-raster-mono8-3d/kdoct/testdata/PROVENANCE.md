# Fixtures

`input.dcm`, `input-blank.dcm` and `input-single.dcm` are copied unchanged from `oct-volume-raster-mono8-3d/mirage/testdata/`; see that directory's PROVENANCE.md (authored synthetic volumes, no patient data: eight retina-like B-scans, four blank B-scans that must degrade, and a single B-scan that is a different family and must degrade).
The synthetic volume carries no pixel spacing and has no clinical ground truth; its frozen response is a regression baseline only.
Real inference is verified by `medomni perception check --samples` on the pinned `MedOmni/family-samples` volumes.

License: authored for MedOmni; Apache-2.0 with this repository.
