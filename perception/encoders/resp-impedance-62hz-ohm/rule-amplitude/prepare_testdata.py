"""Synthetic calibrated WFDB signal; Apache-2.0."""
from pathlib import Path
import numpy as np
import wfdb
root = Path(__file__).parent / "testdata"
wfdb.wrsamp("resp", fs=62.4725, units=["Ohm"], sig_name=["Resp"],
            p_signal=np.tile(np.array([[-10.], [10.]]), (125, 1)),
            fmt=["16"], write_dir=str(root))
(root / "input.hea").write_text((root / "resp.hea").read_text())
(root / "resp.hea").unlink()
(root / "input-empty.hea").write_bytes(b"")
