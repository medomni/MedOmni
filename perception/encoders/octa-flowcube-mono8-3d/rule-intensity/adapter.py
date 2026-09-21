"""Uncalibrated image-intensity features; no segmentation or disease prediction."""
import numpy as np
from contract import Degraded, labels
FAMILY = "octa-flowcube-mono8-3d"


def encode(sample, options):
    pixels = sample["pixels"]
    if not pixels.size or not np.isfinite(pixels).all():
        raise Degraded("empty or non-finite pixels")
    histogram = np.bincount(pixels.reshape(-1), minlength=256)
    probabilities = histogram[histogram > 0] / pixels.size
    items = [
        dict(label="intensity_mean", value=float(np.mean(pixels, dtype=np.float64)), unit="stored-value"),
        dict(label="intensity_std", value=float(np.std(pixels, dtype=np.float64)), unit="stored-value"),
        dict(label="zero_fraction", value=float(histogram[0]/pixels.size), unit="1"),
        dict(label="saturated_fraction", value=float(histogram[255]/pixels.size), unit="1"),
        dict(label="intensity_entropy", value=float(-np.sum(probabilities*np.log2(probabilities))), unit="bit"),
        dict(label="frame_count", value=int(pixels.shape[0]) if pixels.ndim == 3 else 1, unit="1"),
    ]
    return [labels(items, "physical")]
