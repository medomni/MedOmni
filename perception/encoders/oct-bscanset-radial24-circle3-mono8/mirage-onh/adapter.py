"""MIRAGE on the optic-nerve-head B-scan set — one embedding for the radial fan.

The same published model as the macular volume encoder, on the one family
whose frames are not a stack. MIRAGE reads a B-scan; this family holds two
geometries, 24 radial lines through the disc and 3 circles around it, and they
are not interchangeable — a circle scan cuts the peripapillary nerve fibre
layer, a radial line crosses the cup.

So only the radial fan is embedded, and the circles are counted and reported
rather than averaged in. Mixing them would produce one vector standing for two
acquisition geometries, which is the kind of average nobody could interpret
afterwards. An encoder for the circle scans is a separate encoder, and this one
says how many it declined.

Card: card.yaml   Contract: perception/spec/container-api.md §5
"""
import contextlib
import os
import sys

import numpy as np
import torch
from PIL import Image

from medomni.perception.runtime import Degraded, embedding, labels

FAMILY = "oct-bscanset-radial24-circle3-mono8"

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
    frames = sample["pixels"]
    if "radial_frames" not in sample:
        # The decoder reports geometry when the file records it. Without it
        # there is no way to tell a radial line from a circle, and embedding
        # all 27 frames would produce one vector standing for two acquisition
        # geometries. Refusing is the honest answer, not a worse average.
        raise Degraded("this file records no per-frame reference coordinates, so radial "
                       "and circle scans cannot be told apart; this encoder embeds the "
                       "radial fan only")
    # Blank frames are a property of the data, but the family decoder reports
    # pixels and geometry alone, so they are measured here and reported rather
    # than silently averaged in.
    blank = {i for i in range(frames.shape[0])
             if int(frames[i].max()) == int(frames[i].min())}
    radial = [i for i in sample["radial_frames"] if i not in blank]
    circle = sample["circle_frames"]
    if not radial:
        raise Degraded("every radial B-scan is blank")
    dropped = len(sample["radial_frames"]) - len(radial)
    if dropped:
        sample["notes"].append(f"{dropped} blank radial B-scan(s) excluded from the average")

    with torch.no_grad():
        vectors = torch.stack([_one_bscan(model, frames[i]) for i in radial])
    pooled = vectors.mean(dim=0)
    if not torch.isfinite(pooled).all():
        raise Degraded("the encoder produced a non-finite embedding")

    sample["notes"].append(
        f"embedding averaged over {len(radial)} radial B-scan(s); "
        f"{len(circle)} circle scan(s) were not embedded — a different geometry, "
        "and averaging the two would stand for neither")
    return [labels([{"label": "n_radial_embedded", "value": float(len(radial))},
                    {"label": "n_circle_excluded", "value": float(len(circle))}],
                   scale="physical"),
            embedding([round(float(v), PRECISION) for v in pooled])]
