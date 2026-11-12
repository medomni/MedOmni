"""ECGFounder — twelve-lead diagnostic statement probabilities, and an embedding.

A Net1D published by the PKU Digital Health group, used as it is: no fine-tuning
and no probe. The released checkpoint carries its trained 150-class head, so the
statements below are the model's own and not ours.

The adapter owns only what is specific to this model — the lead order it expects,
the ten-second window, and the normalization it was trained with. Reading the
record and naming its leads is family work and happens upstream, in
medomni.perception.runtime.

Card: card.yaml   Interface: src/medomni/perception/runtime/adapter.py
"""
import os
import sys

import numpy as np
import torch
from scipy.signal import resample

from medomni.perception.runtime import BadRequest, Degraded, embedding, labels
from medomni.perception.runtime.helpers import check_norm_unused

FAMILY = "ecg-1lead-200hz-uv"

# The image bakes the upstream source and the weights in, and points these at
# them, so the container reads no network. The source is on the path rather than
# copied beside this file, so that net1d.py stays the file upstream published.
LOCAL_ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.environ.get("ECGFOUNDER_SOURCE", os.path.join(LOCAL_ROOT, "assets/source"))
WEIGHTS = os.environ.get("ECGFOUNDER_WEIGHTS", os.path.join(LOCAL_ROOT, "assets/weights/1_lead_ECGFounder.pth"))
LABEL_FILE = os.environ.get("ECGFOUNDER_LABELS", os.path.join(LOCAL_ROOT, "assets/source/tasks.txt"))

INPUT_SAMPLES = 5000       # the checkpoint input width
SOURCE_SAMPLES = 2000
N_CLASSES = 150
EMBED_DIM = 1024
PRECISION = 4

# The order the checkpoint expects: standard limb-lead order, aVL before aVF.
# The family declares aVF before aVL, so the adapter reorders. Upstream's
# dataset.py does the same thing when it maps MIMIC's order onto the model's.
# The architecture as published with the weights. These are not tunable: every
# value is fixed by the shape of the checkpoint.
_ARCHITECTURE = dict(
    in_channels=1,
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


_check_norm_unused = check_norm_unused  # shared with the other ECGFounder heads


def _read_labels():
    """The head's vocabulary, from the upstream file at the pinned revision.

    The card declares the same list. Keeping the two independent is deliberate:
    `medomni perception check` compares what the adapter emits against what the card
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
    unknown = set(options) - {"_model", "start_sec"}
    if unknown:
        raise BadRequest("unknown ECGFounder option(s): " + ", ".join(sorted(unknown)))
    start = options.get("start_sec", 0)
    if isinstance(start, bool) or not isinstance(start, (int, float)) or start < 0:
        raise BadRequest("start_sec must be a non-negative number")
    model = options["_model"]["model"]
    names = options["_model"]["labels"]
    first = round(start * sample["rate_hz"])
    if sample["n_samples"] - first < SOURCE_SAMPLES:
        raise Degraded("the selected ECG interval must contain ten complete seconds")

    values = np.asarray(sample["channels"]["ecg"][first:first + SOURCE_SAMPLES], dtype=float)
    selected = "the declared ECG channel"

    if not np.isfinite(values).all() or np.ptp(values) == 0:
        raise Degraded("the selected ECG segment must be finite and non-flat")
    signal = resample(values, INPUT_SAMPLES)
    signal = (signal - signal.mean()) / (signal.std() + 1e-8)
    with torch.no_grad():
        logits, features = model(torch.from_numpy(signal).float()[None, None, :])
        scores = torch.sigmoid(logits)[0]
    sample["notes"].append(
        f"selected {selected} from [{start:g},{start + 10:g}) seconds; "
        "resampled to 500 Hz; global z-score")
    items = [{"label": name, "value": round(float(score), PRECISION)} for name, score in zip(names, scores)]
    vector = [round(float(value), PRECISION) for value in features[0]]
    return [labels(items, scale="probability"), embedding(vector)]
