"""Protect electrode identity when EEG files use a different channel order."""
import tempfile
import unittest
from pathlib import Path

import edfio
import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "perception"
from ._runtime import contract  # noqa: E402


class ScalpEegTests(unittest.TestCase):
    def test_channel_order_is_by_name_and_missing_electrodes_fail(self):
        root = Path(__file__).resolve().parent / 'fixtures/eeg-scalp-1020-19ch-200hz-uv'
        record = edfio.read_edf(root/'input.edf')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'input.edf'
            edfio.Edf(list(reversed(record.signals))).write(path)
            sample = contract.read_family('eeg-scalp-1020-19ch-200hz-uv',path,Path(tmp))
            self.assertEqual('fp1',sample['order'][0])
            source = next(s for s in record.signals if s.label=='fp1')
            np.testing.assert_allclose(sample['channels']['fp1'],source.data,atol=.01)
            edfio.Edf(list(record.signals)[1:]).write(path)
            with self.assertRaises(contract.Degraded):
                contract.read_family('eeg-scalp-1020-19ch-200hz-uv',path,Path(tmp))
