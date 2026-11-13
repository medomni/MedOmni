"""Photon-histogram moments, explicitly not fitted fluorescence lifetimes."""
import numpy as np
from medomni.perception.runtime import Degraded, labels
FAMILY = "flio-tcspc-256x256x1024bin-u16"


def encode(sample, options):
    pixels = sample["pixels"]
    # Sum in uint64 so per-pixel uint16 counts cannot overflow.
    bins = pixels.sum(axis=(1, 2), dtype=np.uint64)
    total = int(bins.sum(dtype=np.uint64))
    if not total:
        raise Degraded("no photons in FLIO histogram")
    probability = bins.astype(np.float64) / total
    centers = np.arange(1024, dtype=np.float64)
    mean = float(probability @ centers)
    std = float(np.sqrt(probability @ ((centers - mean) ** 2)))
    sample["notes"].append("Raw arrival-bin moments; no background subtraction, instrument-response correction or lifetime fitting.")
    return [labels([
        dict(label="photon_count", value=total, unit="count"),
        dict(label="mean_arrival_bin", value=mean, unit="bin"),
        dict(label="std_arrival_bin", value=std, unit="bin"),
        dict(label="peak_bin", value=int(np.argmax(bins)), unit="bin"),
        dict(label="nonzero_pixel_fraction", value=float(np.count_nonzero(pixels.sum(axis=0, dtype=np.uint64)) / (256*256)), unit="1"),
    ], "physical")]
