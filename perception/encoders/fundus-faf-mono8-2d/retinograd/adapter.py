"""Retinograd-AI — is this autofluorescence frame gradable?

An Inception-ResNet-v2 published by Eye2Gene, used as it is: no fine-tuning and
no probe. It answers one question — whether a FAF image is of sufficient
quality to be read at all — and that is worth an encoder of its own, because
every other piece of FAF evidence is worth less when the answer is no.

The adapter owns only what is specific to this model: the RGB expansion, the
768x768 resize and the plain [0,1] scaling the upstream script uses, with no
normalization. Reading the DICOM, and collapsing a three-plane colour container
to the one plane this family declares, is family work and already happens in
medomni.perception.runtime.

Card: card.yaml   Interface: src/medomni/perception/runtime/adapter.py
"""
import os

import numpy as np
import torch
from PIL import Image

from medomni.perception.runtime import Degraded, labels

FAMILY = "fundus-faf-mono8-2d"

WEIGHTS = os.environ.get(
    "RETINOGRAD_WEIGHTS",
    "/opt/weights/FAF_inception_resenet_2Class_classification.pth")

# The published inference script: PIL RGB, Resize((768, 768)), ToTensor(). No
# mean/std normalization — ToTensor alone, so pixels reach the network in
# [0, 1]. Reproducing that exactly matters more than any improvement on it.
INPUT_SIZE = 768
N_CLASSES = 2
PRECISION = 4

# Class index -> label, from the upstream README: "Class 0: Ungradable",
# "Class 1: Gradable". The card declares the same two, independently.
CLASS_LABELS = ("faf_ungradable", "faf_gradable")


def load():
    """Build the architecture and read the checkpoint once, at start."""
    import timm

    # pretrained=False: upstream passes True, which downloads ImageNet weights
    # and then overwrites every one of them with the checkpoint below. In an
    # image built to run offline that download is both useless and fatal.
    model = timm.create_model("inception_resnet_v2", pretrained=False,
                              num_classes=N_CLASSES)
    # The file is baked into the image and verified by sha256 during the build,
    # so it is not untrusted input here. It is a training checkpoint, holding
    # more than the weights, which a restricted load rejects.
    checkpoint = torch.load(WEIGHTS, map_location="cpu", weights_only=False)
    state = checkpoint["model_state_dict"] if "model_state_dict" in checkpoint else checkpoint
    # Strictly: a checkpoint that does not describe this network would
    # otherwise load anyway and answer with partly random weights.
    model.load_state_dict(state, strict=True)
    if model.classif.out_features != N_CLASSES:
        raise RuntimeError(f"the head emits {model.classif.out_features} classes, "
                           f"expected {N_CLASSES}")
    model.eval()
    return model


def encode(sample, options):
    model = options["_model"]
    plane = sample["pixels"]
    if plane.ndim != 2:
        raise Degraded("this encoder reads one plane; the family decoder returned "
                       f"{plane.ndim} dimensions")
    if int(plane.max()) == int(plane.min()):
        # The family decoder reports what the file holds; whether a frame is
        # worth answering about is this encoder's call. A classifier that
        # answered 0.997 for a blank frame would be stating a fact about
        # nothing, so the input is refused instead.
        raise Degraded("the frame is blank; every pixel has the same value")
    if min(plane.shape) < 32:
        raise Degraded(f"the frame is {plane.shape[0]}x{plane.shape[1]}; a strip that "
                       "small is not a fundus image, and resizing it to 768 square "
                       "would invent detail the acquisition never held")

    # One plane to three: the network's first convolution has three input
    # channels, and the published script reaches them with PIL's convert('RGB'),
    # which repeats the grey plane. Repeating it here is the same operation,
    # stated rather than hidden behind a format conversion.
    image = Image.fromarray(np.ascontiguousarray(plane), mode="L").convert("RGB")
    image = image.resize((INPUT_SIZE, INPUT_SIZE), Image.BILINEAR)
    tensor = torch.from_numpy(np.asarray(image, dtype=np.uint8).copy())
    tensor = tensor.permute(2, 0, 1).float().div_(255.0).unsqueeze(0)

    with torch.no_grad():
        probabilities = torch.softmax(model(tensor), dim=1)[0]

    items = [{"label": name, "value": round(float(p), PRECISION)}
             for name, p in zip(CLASS_LABELS, probabilities)]
    return [labels(items, scale="probability")]
