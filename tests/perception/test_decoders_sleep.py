"""Ensure channel order never substitutes for EEG reference identity."""
import tempfile
import unittest
from pathlib import Path
import edfio
import numpy as np

from ._runtime import contract  # noqa: E402


class SleepDecoderTests(unittest.TestCase):
    def test_declared_prefix_and_components_are_used_by_the_family_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'sample.edf')
            names = ['EEG F3-A2', 'EEG F4-A1', 'EEG C3-A2',
                     'EEG C4-A1', 'EEG O1-A2', 'EEG O2-A1']
            edfio.Edf([edfio.EdfSignal(
                np.arange(200), 200, label=name, physical_dimension='uV')
                for name in names]).write(path)

            sample = contract.read_family('eeg-sleep-6ch-200hz-uv', path)

        self.assertEqual(
            ['f3-m2', 'f4-m1', 'c3-m2', 'c4-m1', 'o1-m2', 'o2-m1'],
            sample['order'],
        )

    def test_unordered_electrodes_are_referenced_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'sample.edf')
            names = ['O2', 'M1', 'C3', 'F4', 'M2', 'C4', 'O1', 'F3']
            levels = dict(zip(names, range(1, 9)))
            edfio.Edf([edfio.EdfSignal(np.full(200, levels[n]), 200, label=n,
                       physical_dimension='uV', physical_range=(-100, 100)) for n in names]).write(path)
            sample = contract.read_family('eeg-sleep-6ch-200hz-uv', path)
            for channel, values in sample['channels'].items():
                left, right = channel.upper().split('-')
                np.testing.assert_allclose(values, levels[left]-levels[right], atol=.01)

    def test_wrong_reference_is_not_used_as_declared_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, 'sample.edf')
            names = ['F3-M2','F4-M1','C3-M1','C4-M1','O1-M2','O2-M1']
            edfio.Edf([edfio.EdfSignal(np.arange(200), 200, label=n, physical_dimension='uV')
                       for n in names]).write(path)
            with self.assertRaisesRegex(contract.Degraded, 'c3-m2'):
                contract.read_family('eeg-sleep-6ch-200hz-uv', path)
