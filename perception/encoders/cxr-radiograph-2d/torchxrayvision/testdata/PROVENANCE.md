# Test data provenance

Every sample this encoder is tested against: where it comes from, and what its
license permits.

## input.png — a synthetic phantom

Not a radiograph. `make_input.py` draws it with the standard library alone: a
dark background, a bright body, two dark lung fields, and a bright spine.

The pixels are the same on every machine, and the file carries no license
question. It proves that the container reads an image, runs the model, and
answers with the labels its card declares. It proves nothing about clinical
behavior.

## input-nih.png — a real chest radiograph

| Field | Value |
|---|---|
| Dataset | NIH ChestX-ray14 (ChestX-ray8) |
| File | `00000001_000.png`, rescaled to 512x512 by the torchxrayvision project |
| Obtained from | https://github.com/mlmed/torchxrayvision/tree/master/tests |
| sha256 | `c8cbe59e6b9b186060dc68e63965658fa6b5b3ada6648d25c189b8b69b43cd4c` |
| Data provider | The NIH Clinical Center |
| Download site | https://nihcc.app.box.com/v/ChestXray-NIHCC |

**License.** The NIH states: "There are no restrictions on the use of the NIH
chest x-ray images." Three things are asked in return, and this section records
all three: the link to the download site above, the citation below, and the
acknowledgement that the NIH Clinical Center is the data provider.

    Wang X, Peng Y, Lu L, Lu Z, Bagheri M, Summers RM. ChestX-ray8:
    Hospital-scale Chest X-ray Database and Benchmarks on Weakly-Supervised
    Classification and Localization of Common Thorax Diseases.
    IEEE CVPR 2017, pages 2097-2106.

**Read this response with care.** ChestX-ray14 is one of the eight datasets
these weights were trained on. The probabilities for this file are in
distribution. They are not evidence that the encoder generalizes.

## What is not here, and why

No MIMIC image. MIMIC-CXR is under the PhysioNet credentialed license, which
does not permit redistribution. A container image goes to a registry, and
anyone who can pull it receives every file inside. MIMIC samples belong in HF
[`MedOmni/family-samples`](https://huggingface.co/datasets/MedOmni/family-samples),
which Data & Task owns. They reach a container through the `/data` mount at run
time, and they are never built into an image.
