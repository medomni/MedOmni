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
these weights were trained on. The scores for this file are in distribution.
They are not evidence that the encoder generalizes.

## input-cc0.png — a second real radiograph, out of sample

| Field | Value |
|---|---|
| Source | Wikimedia Commons, `File:Chest_Xray_PA_3-8-2010.png` |
| Author | Stillwaterising, own work |
| License | CC0 1.0 Universal, a public domain dedication |
| Source sha256 | `a43431b089a6dfab031c10eceef6c821e4f326913bf9015f73f4a1f0446d2be1` |
| This file sha256 | `03266151c0817945ae7f5d9f03d9c870214c77bc31a552584b035c61ef944f60` |

CC0 asks for nothing in return. The author is named here because attribution is
good practice, and not because the license requires it.

**Why this file is here.** The NIH sample is in distribution. This radiograph
was uploaded to Wikimedia Commons as the work of one person, and it comes from
no hospital dataset release, so these weights have not seen it. The two files
together show the difference, in place of a warning that a reader must take on
trust.

**What was changed, and what was not.** The source is 2412x1956 RGBA, and the
three color planes hold equal values. Taking one plane is therefore lossless,
and no tone conversion happened. The image was then reduced to fit 1024 pixels,
because 4.2 MB does not belong in a git repository. The recipe, with Pillow
12.3.0:

    import numpy as np
    from PIL import Image
    plane = np.asarray(Image.open("Chest_Xray_PA_3-8-2010.png"))[..., 0]
    img = Image.fromarray(plane, mode="L")
    img.thumbnail((1024, 1024), Image.LANCZOS)
    img.save("input-cc0.png", optimize=True)

## What is not here, and why

No MIMIC image. MIMIC-CXR is under the PhysioNet credentialed license, which
does not permit redistribution. A container image goes to a registry, and
anyone who can pull it receives every file inside. MIMIC samples belong in HF
[`MedOmni/family-samples`](https://huggingface.co/datasets/MedOmni/family-samples),
which Data & Task owns. They reach a container through the `/data` mount at run
time, and they are never built into an image.
