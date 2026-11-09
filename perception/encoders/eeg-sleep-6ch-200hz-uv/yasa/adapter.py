"""Stage C3-M2 with the bundled, pinned EEG-only YASA model."""
import hashlib
from pathlib import Path
import mne
import numpy as np
import yasa
from medomni.perception.runtime import Degraded, events

FAMILY = 'eeg-sleep-6ch-200hz-uv'
MODEL_SHA256 = '330c1afdc86396e0b6d9f1294d4c4796beb5f7e7cd38be424c10feae98867e31'


def load():
    path = Path(yasa.__file__).parent / 'classifiers/clf_eeg_lgb_0.5.0.joblib'
    if hashlib.sha256(path.read_bytes()).hexdigest() != MODEL_SHA256:
        raise RuntimeError('YASA classifier checksum does not match the card')
    return path


def encode(sample, options):
    values = sample['channels']['c3-m2']
    if len(values) < 300 * 200:
        raise Degraded('YASA requires at least five minutes of EEG')
    if not np.isfinite(values).all() or np.ptp(values) == 0:
        raise Degraded('C3-M2 contains missing values or is flat')
    end = len(values) // 6000 * 6000
    if end != len(values):
        sample['notes'].append('incomplete trailing 30-second epoch discarded')
    raw = mne.io.RawArray(values[None, :end] * 1e-6,
                         mne.create_info(['C3-M2'], 200, ['eeg']), verbose=False)
    stages = yasa.SleepStaging(raw, eeg_name='C3-M2').predict(path_to_model=str(options['_model']))
    names = {'WAKE': 'Wake', 'N1': 'N1', 'N2': 'N2', 'N3': 'N3', 'REM': 'REM'}
    return [events([dict(label=names[str(stage)], t_start=i*30, t_end=(i+1)*30)
                    for i, stage in enumerate(stages.hypno)])]
