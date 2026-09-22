"""Deterministic synthetic EDF; Apache-2.0. No patient recordings."""
from pathlib import Path
import datetime
import edfio
import numpy as np

root = Path(__file__).parent / "testdata"
signals = []
for name, rate, unit in [("position", 10, "")]:
    # Integer endpoints and symmetric square wave give mean 0, RMS 10, PTP 20.
    values = np.tile(np.array([-10., 10.]), int(rate * 2))
    signals.append(edfio.EdfSignal(values, rate, label=name, physical_dimension=unit,
                                  physical_range=(-10, 10)))
edfio.Edf(signals, starttime=datetime.time(0), patient=edfio.Patient(code="synthetic"),
          recording=edfio.Recording(startdate=datetime.date(2024, 1, 1))).write(root / "input.edf")
(root / "input-empty.edf").write_bytes(b"")
