"""Single-lead ECG measurements using NeuroKit2."""
import neurokit2 as nk
import numpy as np
from medomni.perception.runtime import Degraded, labels

FAMILY = 'ecg-1lead-200hz-uv'


def encode(sample, options):
    signal = sample['channels']['ecg']
    rate = sample['rate_hz']
    if not 30 * rate <= len(signal) <= 1800 * rate:
        raise Degraded('ECG requires 30 seconds to 30 minutes')
    if not np.isfinite(signal).all() or np.ptp(signal) == 0:
        raise Degraded('ECG contains missing samples or is flat')
    clean = nk.ecg_clean(signal, sampling_rate=rate)
    _, info = nk.ecg_peaks(clean, sampling_rate=rate, correct_artifacts=False)
    peaks = info['ECG_R_Peaks']
    if len(peaks) < 4:
        raise Degraded('fewer than four R-peaks were detected')
    rr = np.diff(peaks) * 1000 / rate
    quality = nk.ecg_quality(clean, rpeaks=peaks, sampling_rate=rate, method='templatematch')
    if not np.isfinite(quality).all():
        raise Degraded('ECG template quality could not be measured')
    measurements = [('heart_rate_mean', 60000 / np.mean(rr), 'beats/min'),
                    ('beat_count', len(peaks), '1'), ('rr_mean', np.mean(rr), 'ms'),
                    ('sdnn', np.std(rr, ddof=1), 'ms'),
                    ('rmssd', np.sqrt(np.mean(np.diff(rr)**2)), 'ms')]
    return [labels([dict(label=n, value=float(v), unit=u) for n, v, u in measurements], 'physical'),
            labels([dict(label='template_quality_mean', value=float(np.mean(quality)))], 'score')]
