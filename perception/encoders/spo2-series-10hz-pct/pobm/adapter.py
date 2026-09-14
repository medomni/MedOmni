"""Oximetry biomarkers through POBM."""
import warnings
import numpy as np
from pobm.obm.desat import DesaturationsMeasures
from pobm.obm.burden import HypoxicBurdenMeasures
from contract import Degraded, labels, events
FAMILY = 'spo2-series-10hz-pct'

def encode(sample, options):
    x = sample['channels']['spo2']
    if not 3000 <= len(x) <= 12*36000:
        raise Degraded('oximetry requires 5 minutes to 12 hours')
    if not np.isfinite(x).all() or np.any(x <= 0) or np.any(x > 100):
        raise Degraded('saturation must be finite and within (0,100] percent')
    if len(x) % 10:
        raise Degraded('oximetry duration must contain whole seconds')
    x = np.median(x.reshape(-1, 10), axis=1)
    sample['notes'].append('10 Hz saturation aggregated to one-second medians for POBM')
    # Restore warning filters changed by the upstream library after the call.
    with warnings.catch_warnings():
        result = DesaturationsMeasures(ODI_Threshold=3).compute(x)
        burden = HypoxicBurdenMeasures(result.begin, result.end, CT_Threshold=90, CA_Baseline=90).compute(x)
    if not np.isfinite(result.ODI):
        raise Degraded('POBM did not return a finite desaturation index')
    items = [dict(label='odi3', value=float(result.ODI), unit='events/h'),
             dict(label='time_below_90_pct', value=float(np.mean(x < 90)*100), unit='%'),
             dict(label='hypoxic_area_below_90', value=float(burden.CA), unit='percentage points'),
             dict(label='desaturation_area_from_max', value=float(burden.AODmax), unit='percentage points'),
             dict(label='desaturation_count', value=len(result.begin), unit='1')]
    return [labels(items, 'physical'), events([dict(label='desaturation', t_start=float(a), t_end=float(b))
            for a,b in zip(result.begin,result.end)])]
