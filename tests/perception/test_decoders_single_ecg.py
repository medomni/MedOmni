"""Protect single-lead timing and detect unit/channel mistakes."""
import json
import tempfile
import unittest
from pathlib import Path

import edfio
import neurokit2 as nk
import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "perception"
from ._runtime import contract  # noqa: E402


class SingleEcgTests(unittest.TestCase):
    def test_declared_source_alias_is_used_by_the_family_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input.edf'
            edfio.Edf([edfio.EdfSignal(
                np.arange(200), 200, label=' ECG I ', physical_dimension='uV')]).write(path)

            sample = contract.read_family('ecg-1lead-200hz-uv', path, Path(tmp))

        self.assertEqual(['ecg'], sample['order'])
        self.assertIn('ecg-i read as ecg', sample['notes'])

    def test_published_beats_survive_conversion_and_detection(self):
        root = ROOT / 'encoders/ecg-1lead-200hz-uv/neurokit2/testdata'
        sample = contract.read_family('ecg-1lead-200hz-uv', root/'input.edf', root)
        clean = nk.ecg_clean(sample['channels']['ecg'], sampling_rate=sample['rate_hz'])
        _, result = nk.ecg_peaks(clean, sampling_rate=sample['rate_hz'])
        detected = np.asarray(result['ECG_R_Peaks']) / sample['rate_hz']
        reference = [b['time_s'] for b in json.loads((root/'reference-beats.json').read_text())
                     if b['symbol'] != '+']
        matched = sum(np.min(np.abs(detected-t)) < .1 for t in reference)
        self.assertGreater(matched/len(reference), .97)
        self.assertLess(abs(len(detected)-len(reference)), 5)

    def test_wrong_units_and_duplicate_channels_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'input.edf'
            for signals in [
                [edfio.EdfSignal(np.arange(200),200,label='ecg',physical_dimension='mV')],
                [edfio.EdfSignal(np.arange(200),200,label='ecg',physical_dimension='uV') for _ in range(2)],
            ]:
                edfio.Edf(signals).write(path)
                with self.assertRaises(contract.Degraded):
                    contract.read_family('ecg-1lead-200hz-uv',path,Path(tmp))
