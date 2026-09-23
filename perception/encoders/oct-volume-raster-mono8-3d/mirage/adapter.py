"""MIRAGE — one embedding for a stack of OCT B-scans.

A multimodal retinal foundation model published by Morano et al. (2025),
pretrained by masked modelling on paired OCT and SLO images. Used as it is: no
fine-tuning and no probe. The released checkpoint carries no classification
head, so what it can give a reader is a representation, not a finding.

Two decisions belong to this adapter, and both are stated in the card because
neither comes from the paper:

  * **The model reads one B-scan; the family is a stack.** Each B-scan is
    encoded on its own and the embeddings are averaged. Averaging is a choice —
    the alternative, encoding only the central B-scan, throws away most of the
    volume — and it is why the response reports how many B-scans went into it.
  * **MIRAGE was pretrained on OCT paired with SLO.** We have no SLO, so only
    the B-scan modality is supplied. The architecture accepts that, and the
    result is the OCT half of a model that was trained to see both.

Card: card.yaml   Contract: perception/spec/container-api.md §5
"""
import contextlib
import os
import sys

import numpy as np
import torch
from PIL import Image

from contract import Degraded, embedding

FAMILY = "oct-volume-raster-mono8-3d"

SOURCE_DIR = os.environ.get("MIRAGE_SOURCE", "/opt/mirage")
WEIGHTS = os.environ.get("MIRAGE_WEIGHTS", "/opt/weights/model.safetensors")

# The published configuration of MIRAGE-Base, from the model card's config.json.
INPUT_SIZE = 512
PATCH_SIZE = 32
MODALITIES = "bscan-slo"      # the architecture the checkpoint describes
SIZE = "base"
EMBED_DIM = 768
PRECISION = 4

# 1 global token + (512/32)^2 = 256 patch tokens. The global token is the one
# summary the encoder itself produces, and it is what this adapter returns.
N_TOKENS = 1 + (INPUT_SIZE // PATCH_SIZE) ** 2


def load():
    """Build the published architecture and read the checkpoint once, at start."""
    if SOURCE_DIR not in sys.path:
        sys.path.insert(0, SOURCE_DIR)
    from safetensors.torch import load_file

    from mirage_hf import MIRAGEWrapper

    # The wrapper prints its configuration to stdout while building. One
    # response is one JSON document on stdout, so that chatter has to go
    # somewhere else; it is kept rather than silenced, on stderr, where the
    # container log already collects everything a person would want to read.
    with contextlib.redirect_stdout(sys.stderr):
        model = MIRAGEWrapper(input_size=INPUT_SIZE, patch_size=PATCH_SIZE,
                              modalities=MODALITIES, size=SIZE)
    # The published safetensors is the wrapper's own state, so every key is
    # prefixed 'model.' while MIRAGEWrapper.load_state_dict forwards to the
    # network inside it. Stripping the prefix is what makes a strict load
    # possible, and strict is the point: a checkpoint that does not describe
    # this network would otherwise load anyway and answer with random weights.
    state = {}
    for key, tensor in load_file(WEIGHTS).items():
        if not key.startswith("model."):
            raise RuntimeError(f"unexpected key in the checkpoint: {key}")
        state[key[len("model."):]] = tensor
    model.load_state_dict(state, strict=True)
    model.eval()
    return model


def _one_bscan(model, plane):
    """One B-scan -> its global token."""
    # Resize to the published input, as the upstream loader does: PIL bilinear
    # on an 8-bit plane, then a plain division by 255. The wrapper documents
    # that it expects values in [0, 1], and no other normalization.
    image = Image.fromarray(np.ascontiguousarray(plane), mode="L")
    image = image.resize((INPUT_SIZE, INPUT_SIZE), Image.BILINEAR)
    tensor = torch.from_numpy(np.asarray(image, dtype=np.uint8).copy())
    tensor = tensor.float().div_(255.0)[None, None, ...]
    tokens = model({"bscan": tensor})
    if tokens.shape[1] != N_TOKENS or tokens.shape[2] != EMBED_DIM:
        raise RuntimeError(f"the encoder returned {tuple(tokens.shape)}, expected "
                           f"(1, {N_TOKENS}, {EMBED_DIM})")
    return tokens[0, 0]


def encode(sample, options):
    model = options["_model"]
    volume = sample["pixels"]
    if volume.ndim != 3:
        raise Degraded(f"this family is a stack of B-scans; the decoder returned "
                       f"{volume.ndim} dimension(s)")
    n_frames = int(volume.shape[0])
    # Which frames carry nothing is a property of the data rather than of this
    # model, but the family decoder reports pixels alone, so it is measured here
    # and reported rather than silently averaged in.
    blank = {i for i in range(n_frames) if int(volume[i].max()) == int(volume[i].min())}
    usable = [i for i in range(n_frames) if i not in blank]
    if not usable:
        raise Degraded("every B-scan is blank")
    if len(usable) < n_frames:
        sample["notes"].append(
            f"{n_frames - len(usable)} blank B-scan(s) excluded from the average")

    with torch.no_grad():
        vectors = torch.stack([_one_bscan(model, volume[i]) for i in usable])
    pooled = vectors.mean(dim=0)
    if not torch.isfinite(pooled).all():
        raise Degraded("the encoder produced a non-finite embedding")

    sample["notes"].append(f"embedding averaged over {len(usable)} B-scan(s)")
    return [embedding([round(float(v), PRECISION) for v in pooled])]
