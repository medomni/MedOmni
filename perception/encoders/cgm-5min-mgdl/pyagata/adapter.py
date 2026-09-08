"""Compute observed-sample CGM metrics with PYAGATA."""
import numpy as np
import pandas as pd
from py_agata.variability import mean_glucose, std_glucose, cv_glucose
from py_agata.time_in_ranges import time_in_given_range
from contract import Degraded, labels

FAMILY = "cgm-5min-mgdl"


def encode(sample, options):
    data = pd.DataFrame({'t': pd.to_datetime(sample['times']), 'glucose': sample['glucose']})
    values = data.glucose.to_numpy()
    if np.isfinite(values).sum() < 2:
        raise Degraded("at least two observed glucose values are required")
    metrics = [
        ('glucose_mean', mean_glucose(data), 'mg/dL'),
        ('glucose_std', std_glucose(data), 'mg/dL'),
        ('glucose_cv', cv_glucose(data), '%'),
        ('percent_70_to_180', time_in_given_range(data, 70., 180., True, True), '%'),
        ('percent_missing', 100 * np.isnan(values).mean(), '%'),
    ]
    if not all(np.isfinite(value) for _, value, _ in metrics):
        raise Degraded("CGM metrics are not finite for this input")
    return [labels([dict(label=name, value=float(value), unit=unit)
                    for name, value, unit in metrics], 'physical')]
