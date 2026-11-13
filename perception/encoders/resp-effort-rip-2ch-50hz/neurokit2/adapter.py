"""Independent breathing measurements from two effort belts."""
import neurokit2 as nk
import numpy as np
from medomni.perception.runtime import Degraded, labels
FAMILY = 'resp-effort-rip-2ch-50hz'

def encode(sample, options):
    rate = sample['rate_hz']
    items = []
    for name in ('thorax', 'abdomen'):
        x = sample['channels'][name]
        if not 60*rate <= len(x) <= 1800*rate:
            raise Degraded('respiration requires 60 seconds to 30 minutes')
        if not np.isfinite(x).all() or np.ptp(x) == 0:
            raise Degraded(f'{name} contains missing samples or is flat')
        clean = nk.rsp_clean(x, sampling_rate=rate, method='khodadad2018')
        _, info = nk.rsp_peaks(clean, sampling_rate=rate, method='khodadad2018')
        peaks = info['RSP_Peaks']
        if len(peaks) < 3:
            raise Degraded(f'{name}: fewer than three respiratory peaks')
        items.extend([dict(label=name+'_breathing_rate_mean', value=float(60*rate/np.mean(np.diff(peaks))), unit='breaths/min'),
                      dict(label=name+'_cycle_count', value=len(peaks)-1, unit='1')])
    return [labels(items, 'physical')]
