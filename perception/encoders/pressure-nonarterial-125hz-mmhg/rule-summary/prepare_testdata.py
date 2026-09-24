"""Synthetic calibrated WFDB pressures; no patient data; Apache-2.0.

input.hea         CVP at the protocol rate, one sample per frame (the published-sample layout).
input-frames.hea  PAP stored two samples per 62.4725 Hz frame beside an ECG lead (the raw MIMIC
                  bedside-segment layout); frames must be expanded to 124.945 Hz, the lead ignored.
input-artifact.hea  CVP held at 398 mmHg (an unzeroed transducer); healthy, but flagged.
input-empty.hea   empty header; degrades."""
from pathlib import Path
import numpy as np
import wfdb

root = Path(__file__).parent / "testdata"
fs = 124.945
n = 1000


def write(name, **kwargs):
    wfdb.wrsamp(name, write_dir=str(root), **kwargs)
    (root / f"input{'' if name == 'cvp' else '-' + name}.hea").write_text((root / f"{name}.hea").read_text())
    (root / f"{name}.hea").unlink()


write("cvp", fs=fs, units=["mmHg"], sig_name=["CVP"], fmt=["16"],
      p_signal=np.tile([[6.0], [10.0]], (n // 2, 1)))
pap = np.tile([10.0, 30.0], n // 2)
ecg = np.zeros(n // 2)
write("frames", fs=fs / 2, units=["mV", "mmHg"], sig_name=["II", "PAP"], fmt=["16", "16"],
      samps_per_frame=[1, 2], e_p_signal=[ecg, pap])
write("artifact", fs=fs, units=["mmHg"], sig_name=["CVP"], fmt=["16"],
      p_signal=np.tile([[397.5], [398.5]], (n // 2, 1)))
(root / "input-empty.hea").write_bytes(b"")
