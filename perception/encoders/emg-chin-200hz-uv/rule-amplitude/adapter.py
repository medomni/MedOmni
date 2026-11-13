"""Descriptive signal amplitude features; no learned or diagnostic claims."""
from medomni.perception.runtime.helpers import amplitude_features

FAMILY = "emg-chin-200hz-uv"


encode = amplitude_features  # shared with the other rule-amplitude encoders
