"""Pulse metrics from the NeuroKit2 Elgendi pipeline."""
import neurokit2 as nk
import numpy as np
from contract import Degraded, labels

FAMILY = 'ppg-waveform-uncal'


def encode(sample, options):
    signal, rate = sample['channels']['pleth'], sample['rate_hz']
    if rate < 25 or len(signal) < 30 * rate:
        raise Degraded('PPG requires at least 30 seconds sampled at 25 Hz or higher')
    if not np.isfinite(signal).all() or np.ptp(signal) == 0:
        raise Degraded('PPG contains missing values or is flat')
    cleaned = nk.ppg_clean(signal, sampling_rate=rate, method='elgendi')
    _, info = nk.ppg_peaks(cleaned, sampling_rate=rate, method='elgendi')
    peaks = info['PPG_Peaks']
    if len(peaks) < 4:
        raise Degraded('fewer than four PPG peaks were detected')
    pulse_rate = nk.signal_rate(peaks, sampling_rate=rate, desired_length=len(signal))
    quality = nk.ppg_quality(cleaned, peaks=peaks, sampling_rate=rate, method='templatematch')
    if not np.isfinite(pulse_rate).all() or not np.isfinite(quality).all():
        raise Degraded('PPG rate or template quality could not be measured')
    items = [dict(label='pulse_rate_'+stat, value=float(fn(pulse_rate)), unit='beats/min')
             for stat, fn in [('mean',np.mean), ('min',np.min), ('max',np.max)]]
    items.append(dict(label='beat_count', value=int(len(peaks)), unit='1'))
    return [labels(items, 'physical'), labels([dict(label='template_quality_mean',
                                                   value=float(np.mean(quality)))], 'score')]
