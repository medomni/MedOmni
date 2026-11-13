"""Uncalibrated image-intensity features; no segmentation or disease prediction."""
from medomni.perception.runtime.helpers import intensity_features
FAMILY = "oct-volume-raster-mono8-3d"


encode = intensity_features  # shared with the other rule-intensity encoders
