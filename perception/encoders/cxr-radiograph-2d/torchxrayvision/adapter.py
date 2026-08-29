"""torchxrayvision — chest-radiograph pathology probabilities.

A DenseNet-121 published by the mlmed group, used as it is: no fine-tuning and
no probe. The adapter owns only what is specific to this model — the intensity
range it was trained on, the center crop, and the resize to 224. Reading the
file is family work and happens upstream, in runtime/contract.py.

Card: card.yaml   Contract: perception/spec/container-api.md §5
"""
import os

import numpy as np
import torch
import torchvision
import torchxrayvision as xrv

from contract import Degraded, labels

FAMILY = "cxr-radiograph-2d"
WEIGHTS = "densenet121-res224-all"
MAXVAL = 255           # the 8-bit range the family declares
PRECISION = 4

# The image bakes the weights in and points this at them, so the container
# reads no network and needs no writable home directory. Unset, the library
# uses ~/.torchxrayvision and downloads on first use.
WEIGHTS_DIR = os.environ.get("XRV_WEIGHTS_DIR") or None

# Model-specific preprocessing, as published with the weights.
_TRANSFORM = torchvision.transforms.Compose([
    xrv.datasets.XRayCenterCrop(),
    xrv.datasets.XRayResizer(224),
])


def load():
    """Read the weights once, at start. The server passes the result to encode."""
    model = xrv.models.DenseNet(weights=WEIGHTS, cache_dir=WEIGHTS_DIR)
    model.eval()
    return model


def encode(sample, options):
    model = options["_model"]
    pixels = sample["pixels"]
    if pixels.size == 0:
        raise Degraded("the image has no pixels")
    if pixels.min() == pixels.max():
        raise Degraded("the image is blank; every pixel has the same value")

    image = xrv.datasets.normalize(pixels.astype(np.float32), MAXVAL)
    image = _TRANSFORM(image[None, ...])
    with torch.no_grad():
        scores = model(torch.from_numpy(image)[None, ...])[0]

    items = [{"label": name, "value": round(float(score), PRECISION)}
             for name, score in zip(model.pathologies, scores) if name]
    return [labels(items, scale="probability")]
