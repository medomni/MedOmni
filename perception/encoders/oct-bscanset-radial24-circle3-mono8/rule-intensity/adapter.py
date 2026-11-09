"""Uncalibrated image-intensity features; no segmentation or disease prediction."""
from medomni.perception.runtime.helpers import intensity_features
FAMILY = "oct-bscanset-radial24-circle3-mono8"


encode = intensity_features  # shared with the other rule-intensity encoders
