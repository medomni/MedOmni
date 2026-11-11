Build from the repository root after your account has access to
[YukunZhou/RETFound_mae_natureCFP](https://huggingface.co/YukunZhou/RETFound_mae_natureCFP).

```sh
uvx --from huggingface_hub hf auth login
uv run perception/encoders/fundus-photography-2d/retfound/prepare_assets.py
medomni perception check perception/encoders/fundus-photography-2d/retfound
```

The preparation step checks the official checkpoint and source hashes.
It copies assets into the ignored `assets/` folder. The token stays in your host credential cache.
The image contains the model, its source, and dependencies, and needs no network access at runtime.
The checkpoint download is about 4 GB. Allow at least 8 GB of container memory.

The adapter uses the upstream `RETFound_mae(global_pool=False)` encoder and returns its normalized class token.
It excludes MAE decoder and classification-head weights, then loads all encoder parameters strictly.
The card records the weight license and preprocessing limits.

Verification status: the pinned checkpoint loaded successfully. The colour fixture produced a finite 1024-value embedding.
The monochrome fixture produced an unhealthy response as required. The frozen responses are in `testdata/expected.json`.

```sh
medomni perception check perception/encoders/fundus-photography-2d/retfound
```
