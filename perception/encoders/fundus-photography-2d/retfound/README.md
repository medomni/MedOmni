Build from the repository root after your account has access to
[YukunZhou/RETFound_mae_natureCFP](https://huggingface.co/YukunZhou/RETFound_mae_natureCFP).

```sh
uvx --from huggingface_hub hf auth login
uv run perception/encoders/fundus-photography-2d/retfound/prepare_assets.py
uv run --with pyyaml perception/registry.py build fundus-photography-2d__retfound
uv run --with pyyaml perception/registry.py test fundus-photography-2d__retfound --docker
```

The preparation step checks the official checkpoint and source hashes.
It copies assets into the ignored `assets/` folder. The token stays in your host credential cache.
The image contains the model, its source, and dependencies, and needs no network access at runtime.
The checkpoint download is about 4 GB. Allow at least 8 GB of container memory.

The adapter uses the upstream `RETFound_mae(global_pool=False)` encoder and returns its normalized class token.
It excludes MAE decoder and classification-head weights, then loads all encoder parameters strictly.
The card records the weight license and preprocessing limits.

Verification status: the dependency image, source imports, DICOM decoding, and monochrome rejection were checked.
Pretrained loading and colour-image inference remain unverified because the official checkpoint returned HTTP 403.
No expected embedding has been invented. After model access is approved, check the real colour fixture and create its baseline:

```sh
uv run --with pyyaml perception/registry.py freeze fundus-photography-2d__retfound --docker
uv run --with pyyaml perception/registry.py test fundus-photography-2d__retfound --docker
```

Confirm that `input.dcm` returns a healthy, finite 1024-value embedding and that `input-monochrome.dcm` returns `healthy: false`.
