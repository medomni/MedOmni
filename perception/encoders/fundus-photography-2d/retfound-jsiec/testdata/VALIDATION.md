# Verification (2026-09-24)

Semantic smoke test (encoder-semantics.md §3), dev image, 117 JSIEC images from the RETFound BENCHMARK.md test split (3 per class for all 39 classes; held out from fine-tuning; not redistributed).

Top-1 94/117 (chance 1/39), top-3 105/117, so the head's class order (the 39 folder names sorted as strings) is wired correctly.
Classes whose true label missed the top 3 at least once: chorioretinal atrophy/coloboma, congenital disc abnormality, fibrosis, fundus neoplasm, optic atrophy, possible glaucoma, severe hypertensive retinopathy, vessel tortuosity.
Example text output: "Top findings: pathological myopia 0.94; myelinated nerve fiber 0.01; central retinal vein occlusion 0.00".
Smoke tests do not establish clinical reliability on this cohort's devices.
