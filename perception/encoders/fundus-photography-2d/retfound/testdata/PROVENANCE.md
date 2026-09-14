# Fixtures

`input.dcm` contains Mikael Häggström's public-domain photograph of a normal left eye.
Source: https://commons.wikimedia.org/wiki/File:Fundus_photograph_of_normal_left_eye.jpg
License: CC0 1.0. See https://creativecommons.org/publicdomain/zero/1.0/.
Citation: Häggström (2014), Medical gallery of Mikael Häggström 2014, DOI 10.15347/wjm/2014.008.

The RGB pixels came from `skimage.data.retina()` in scikit-image 0.25.2.
They were resized from 1411 by 1411 to 512 by 512 with Pillow bicubic interpolation.
A new DICOM Secondary Capture wrapper stores these pixels without compression.
The wrapper contains no patient identifiers or asserted acquisition metadata.

`input-monochrome.dcm` is an authored grayscale ramp. It checks rejection of one-plane input.
It is not a retinal acquisition. Private MedOmni fundus samples are infrared and are unsuitable for colour-model verification.

Source RGB pixel SHA-256: `3670e389d0dae9f755cc1bb7e4da4c3d2cdf10eba2dc3060836d8d4b8024d860`

# Baseline

`expected.json` contains responses from the checkpoint hash in `card.yaml`.
The validation copy came from [sabarimj/retfound](https://huggingface.co/sabarimj/retfound/commit/7792ae44eb692fb830fb0390d181f5f2bfa00e58).
Its SHA-256 matched the pinned official checkpoint exactly.
The mirror was used only for local validation. The build recipe continues to use the official gated source.
