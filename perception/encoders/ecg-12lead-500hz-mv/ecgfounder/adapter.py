"""ECGFounder — twelve-lead diagnostic statement probabilities, and an embedding.

A Net1D published by the PKU Digital Health group, used as it is: no fine-tuning
and no probe. The released checkpoint carries its trained 150-class head, so the
statements below are the model's own and not ours.

The adapter owns only what is specific to this model — the lead order it expects,
the ten-second window, and the normalization it was trained with. Reading the
record and naming its leads is family work and happens upstream, in
runtime/contract.py.

Card: card.yaml   Contract: perception/spec/container-api.md §5
"""
import os
import sys

import numpy as np
import torch

from contract import Degraded, embedding, labels

FAMILY = "ecg-12lead-500hz-mv"

# The image bakes the upstream source and the weights in, and points these at
# them, so the container reads no network. The source is on the path rather than
# copied beside this file, so that net1d.py stays the file upstream published.
SOURCE_DIR = os.environ.get("ECGFOUNDER_SOURCE", "/opt/ecgfounder")
WEIGHTS = os.environ.get("ECGFOUNDER_WEIGHTS", "/opt/weights/12_lead_ECGFounder.pth")
LABEL_FILE = os.environ.get("ECGFOUNDER_LABELS", "/opt/ecgfounder/tasks.txt")

INPUT_SAMPLES = 5000       # 500 Hz x 10 s, the width the checkpoint declares
N_CLASSES = 150
EMBED_DIM = 1024
PRECISION = 4

# The order the checkpoint expects: standard limb-lead order, aVL before aVF.
# The family declares aVF before aVL, so the adapter reorders. Upstream's
# dataset.py does the same thing when it maps MIMIC's order onto the model's.
MODEL_LEAD_ORDER = ("I", "II", "III", "aVR", "aVL", "aVF",
                    "V1", "V2", "V3", "V4", "V5", "V6")

# The architecture as published with the weights. These are not tunable: every
# value is fixed by the shape of the checkpoint.
_ARCHITECTURE = dict(
    in_channels=12,
    base_filters=64,
    ratio=1,
    filter_list=[64, 160, 160, 400, 400, 1024, 1024],
    m_blocks_list=[2, 2, 2, 3, 3, 4, 4],
    kernel_size=16,
    stride=2,
    groups_width=16,
    n_classes=N_CLASSES,
    # The checkpoint was trained with neither, and _check_norm_unused below
    # verifies that rather than trusting it.
    use_bn=False,
    use_do=False,
)


def _check_norm_unused(state):
    """The checkpoint carries BatchNorm tensors, and the network runs without them.

    That pairing looks like a mistake — weights loaded and then ignored — so it
    is checked instead of trusted. In the published checkpoint every BatchNorm
    tensor is still at its initialization value: scale one, shift zero, running
    mean zero, running variance one, no batches tracked. That is what a network
    trained with use_bn=False leaves behind, and it is why running it with
    use_bn=False discards nothing.

    A future checkpoint with trained statistics would be silently wrong here, so
    it must fail at start rather than answer.
    """
    at_init = {"weight": 1.0, "bias": 0.0, "running_mean": 0.0, "running_var": 1.0,
               "num_batches_tracked": 0}
    for key, tensor in state.items():
        field = key.rsplit(".", 1)[-1]
        if "bn" not in key or field not in at_init:
            continue
        if not torch.all(tensor.to(torch.float64) == at_init[field]):
            raise RuntimeError(
                f"{key} holds trained statistics, but this network runs with "
                "use_bn=False and would ignore them. Refusing to answer with a "
                "model that is not the one the weights describe.")


def _read_labels():
    """The head's vocabulary, from the upstream file at the pinned revision.

    The card declares the same list. Keeping the two independent is deliberate:
    registry.py test compares what the adapter emits against what the card
    declares, which only means something while they come from different places.
    """
    names = [line.strip() for line in open(LABEL_FILE, encoding="utf-8")
             if line.strip()]
    if len(names) != N_CLASSES:
        raise RuntimeError(f"{LABEL_FILE} lists {len(names)} labels, "
                           f"the head emits {N_CLASSES}")
    return names


def load():
    """Read the weights once, at start. The server passes the result to encode."""
    if SOURCE_DIR and SOURCE_DIR not in sys.path:
        sys.path.insert(0, SOURCE_DIR)
    from net1d import Net1D

    model = Net1D(return_features=True, **_ARCHITECTURE)
    # The file is baked into the image and pinned by sha256, verified during the
    # build, so it is not untrusted input at run time. It holds an optimizer
    # state and a numpy scalar besides the weights, which a restricted load
    # rejects.
    checkpoint = torch.load(WEIGHTS, map_location="cpu", weights_only=False)
    state = checkpoint["state_dict"]
    _check_norm_unused(state)
    # Strictly: upstream loads with strict=False, which would let a checkpoint
    # that does not describe this network load anyway and answer with random
    # weights. Every key in the published file matches, so nothing is lost.
    model.load_state_dict(state, strict=True)
    if model.dense.out_features != N_CLASSES or model.dense.in_features != EMBED_DIM:
        raise RuntimeError(f"the head is {model.dense.in_features} -> "
                           f"{model.dense.out_features}, expected "
                           f"{EMBED_DIM} -> {N_CLASSES}")
    model.eval()
    return {"model": model, "labels": _read_labels()}


def encode(sample, options):
    model = options["_model"]["model"]
    names = options["_model"]["labels"]
    channels = sample["channels"]

    if sample["n_samples"] < INPUT_SAMPLES:
        raise Degraded(
            f"the record is {sample['n_samples']} samples at "
            f"{sample['rate_hz']:g} Hz, and this encoder reads ten seconds "
            f"({INPUT_SAMPLES} samples). A shorter record is not stretched to fit, "
            "because that would change the rate the model sees.")

    # Ten seconds from the start. The window is the adapter's to choose, and the
    # card says which one it chose.
    leads = np.stack([channels[name][:INPUT_SAMPLES] for name in MODEL_LEAD_ORDER])

    blank = [name for name, values in zip(MODEL_LEAD_ORDER, leads)
             if not np.isfinite(values).any()]
    if blank:
        raise Degraded("this encoder needs all twelve leads, and these carry no "
                       "usable sample: " + ", ".join(blank))
    if not np.isfinite(leads).all():
        gaps = int((~np.isfinite(leads)).sum())
        leads = np.nan_to_num(leads, nan=0.0, posinf=0.0, neginf=0.0)
        sample["notes"].append(f"{gaps} non-finite sample(s) read as zero")
    if leads.min() == leads.max():
        raise Degraded("the recording is flat; every sample has the same value")

    # Normalization as published with the weights: one z-score over the whole
    # twelve-lead window, not per lead. This is why the family's mV declaration
    # does not change the answer — absolute scale cancels here.
    signal = (leads - leads.mean()) / (leads.std() + 1e-8)

    with torch.no_grad():
        logits, features = model(torch.from_numpy(signal).float()[None, ...])
        scores = torch.sigmoid(logits)[0]

    items = [{"label": name, "value": round(float(score), PRECISION)}
             for name, score in zip(names, scores)]
    vector = [round(float(value), PRECISION) for value in features[0]]
    return [labels(items, scale="probability"), embedding(vector)]
