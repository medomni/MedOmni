"""The physiology level (part 5b): each planted fact is read back by an analysis independent of the generator.

The generators place beats from a sum-of-Gaussians model and breaths from neurokit2's simulator; the read-back uses
neurokit2's peak detection, Welch band power and plain thresholds.
"""
import importlib.util
import time
import warnings
from pathlib import Path

import numpy as np
import pytest

from medomni.core import families
from medomni.core.families.check import conforms
from medomni.core.families.dummy import make_dummy, ranges
from medomni.core.families.dummy.datasets import make_dataset
from medomni.core.families.dummy.subject import EPOCH, subject
from medomni.core.testing import DATASETS

REPO = Path(__file__).resolve().parents[2]
SEED = 3
KEY = "DUMMY-1"
warnings.filterwarnings("ignore", category=DeprecationWarning)


def fam(fid):
    return families.get(fid, REPO)


def edf(path):
    import pyedflib

    r = pyedflib.EdfReader(str(path))
    try:
        return {r.getLabel(i).strip().lower(): (r.readSignal(i), r.getSampleFrequency(i))
                for i in range(r.signals_in_file)}
    finally:
        r.close()


def wfdb_record(path):
    import wfdb

    rec = wfdb.rdrecord(str(path.with_suffix("")))
    return {n.lower(): (rec.p_signal[:, i], rec.fs) for i, n in enumerate(rec.sig_name)}


def planted_hr(seconds):
    b = subject(SEED, KEY).beats(seconds)
    return 60.0 / float(np.mean(np.diff(b)))


def hr_ecg(x, fs):
    import neurokit2 as nk

    _, info = nk.ecg_peaks(x, sampling_rate=fs)
    return 60.0 * len(info["ECG_R_Peaks"]) / (len(x) / fs)


def hr_ppg(x, fs):
    import neurokit2 as nk

    _, info = nk.ppg_peaks(x, sampling_rate=fs)
    return 60.0 * len(info["PPG_Peaks"]) / (len(x) / fs)


def br(x, fs):
    import neurokit2 as nk

    _, info = nk.rsp_peaks(nk.rsp_clean(x, sampling_rate=fs), sampling_rate=fs)
    return 60.0 * len(info["RSP_Peaks"]) / (len(x) / fs)


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    out = tmp_path_factory.mktemp("physio")
    fids = ["ecg-1lead-200hz-uv", "ecg-monitor-3to5lead-250hz-continuous", "ecg-12lead-500hz-mv", "ppg-waveform-uncal",
            "abp-waveform-125hz-mmhg", "resp-effort-rip-2ch-50hz", "resp-flow", "resp-impedance-62hz-ohm",
            "psg-cardiorespiratory-4ch-200hz-mixed", "eeg-sleep-6ch-200hz-uv", "eog-2ch-200hz-uv",
            "emg-chin-200hz-uv", "spo2-series-10hz-pct", "pulse-rate-10hz-bpm", "capnography-mmhg"]
    return {f: make_dummy(fam(f), SEED, out, subject=KEY) for f in fids}


@pytest.mark.parametrize("fid", sorted(families.load_registry(REPO)))
def test_format_level_still_conforms(fid, tmp_path):
    p = make_dummy(fam(fid), SEED, tmp_path, level="format")
    assert conforms(fam(fid), p) == []


def test_physiology_files_conform(made):
    for fid, p in made.items():
        assert conforms(fam(fid), p) == [], fid


@pytest.mark.parametrize("fid, reader, channel", [
    ("ecg-1lead-200hz-uv", edf, "ecg"),
    ("ecg-monitor-3to5lead-250hz-continuous", wfdb_record, "ii"),
    ("ecg-12lead-500hz-mv", wfdb_record, "ii"),
])
def test_heart_rate_from_ecg(made, fid, reader, channel):
    x, fs = reader(made[fid])[channel]
    assert abs(hr_ecg(x, fs) - planted_hr(len(x) / fs)) <= 3


@pytest.mark.parametrize("fid, reader, channel", [
    ("ppg-waveform-uncal", edf, "pleth"),
    ("abp-waveform-125hz-mmhg", wfdb_record, "abp"),
])
def test_heart_rate_from_pulse_waves(made, fid, reader, channel):
    x, fs = reader(made[fid])[channel]
    assert abs(hr_ppg(x, fs) - planted_hr(len(x) / fs)) <= 3


def test_arterial_pressure_is_in_the_subjects_range(made):
    x, _ = wfdb_record(made["abp-waveform-125hz-mmhg"])["abp"]
    s = subject(SEED, KEY)
    assert abs(np.percentile(x, 99) - s.sbp) < 5 and abs(np.percentile(x, 1) - s.dbp) < 5


@pytest.mark.parametrize("fid, reader, channel", [
    ("resp-effort-rip-2ch-50hz", edf, "thorax"),
    ("resp-effort-rip-2ch-50hz", edf, "abdomen"),
    ("resp-flow", edf, "thermistor"),
    ("resp-impedance-62hz-ohm", wfdb_record, "resp"),
    ("psg-cardiorespiratory-4ch-200hz-mixed", edf, "thx"),
])
def test_breathing_rate(made, fid, reader, channel):
    x, fs = reader(made[fid])[channel]
    assert abs(br(x, fs) - subject(SEED, KEY).br) <= 2


def test_capnography_breathes(made):
    x, fs = edf(made["capnography-mmhg"])["etco2-waveform"]
    expirations = np.sum(np.diff((x > 20).astype(int)) == 1)
    assert abs(60 * expirations / (len(x) / fs) - subject(SEED, KEY).br) <= 2
    assert 33 <= np.percentile(x, 90) <= 43  # end-tidal CO2, mmHg


def test_one_subject_one_heart_rate(made):
    sig = edf(made["psg-cardiorespiratory-4ch-200hz-mixed"])
    (ecg, fs), (pleth, _) = sig["ecg"], sig["pleth"]
    assert abs(hr_ecg(ecg, fs) - hr_ppg(pleth, fs)) <= 3


def _band(x, fs, lo, hi):
    from scipy.signal import welch

    f, p = welch(x, fs=fs, nperseg=int(4 * fs))
    return float(p[(f >= lo) & (f < hi)].sum() / p[(f >= 0.5) & (f < 30)].sum())


def test_sleep_stages_in_the_eeg(made):
    x, fs = edf(made["eeg-sleep-6ch-200hz-uv"])["c4-m1"]
    s = subject(SEED, KEY)
    stages = s.stages(len(x) / fs)
    assert set(stages) == {"W", "N1", "N2", "N3", "REM"}
    epochs = {st: [x[int(i * EPOCH * fs):int((i + 1) * EPOCH * fs)] for i, e in enumerate(stages) if e == st]
              for st in set(stages)}
    power = {st: {b: np.mean([_band(e, fs, *r) for e in es]) for b, r in
                  {"delta": (0.5, 2), "alpha": (8, 12), "sigma": (12, 15)}.items()} for st, es in epochs.items()}
    assert max(power, key=lambda st: power[st]["delta"]) == "N3"
    assert max(power, key=lambda st: power[st]["alpha"]) == "W"
    assert power["N2"]["sigma"] > max(power["N1"]["sigma"], power["N3"]["sigma"])


def test_eog_channels_move_opposite(made):
    sig = edf(made["eog-2ch-200hz-uv"])
    assert np.corrcoef(sig["e1-m2"][0], sig["e2-m1"][0])[0, 1] < -0.5


def test_chin_tone_lowest_in_rem(made):
    x, fs = edf(made["emg-chin-200hz-uv"])["chin1-chin2"]
    stages = subject(SEED, KEY).stages(len(x) / fs)
    rms = {st: np.mean([np.sqrt(np.mean(x[int(i * EPOCH * fs):int((i + 1) * EPOCH * fs)] ** 2))
                        for i, e in enumerate(stages) if e == st]) for st in set(stages)}
    assert min(rms, key=rms.get) == "REM" and max(rms, key=rms.get) == "W"


def test_desaturations_counted(made):
    x, fs = edf(made["spo2-series-10hz-pct"])["spo2"]
    s = subject(SEED, KEY)
    low = (x < np.median(x) - 3).astype(int)
    dips = int(np.sum(np.diff(np.concatenate([[0], low])) == 1))
    assert dips == len([d for d in s.desaturations if d + s.DESAT_SECONDS <= len(x) / fs])
    assert dips >= 1


def test_pulse_rate_follows_the_heart(made):
    x, _ = edf(made["pulse-rate-10hz-bpm"])["pulse"]
    assert abs(float(np.mean(x)) - planted_hr(len(x) / 10)) <= 3


def test_table_values_in_published_ranges(tmp_path):
    d = make_dataset(DATASETS / "dummy-mimic", tmp_path / "m")
    import csv

    rows = list(csv.DictReader(open(d.root / "hosp/labevents.csv")))
    planted = {(e["subject"], e["value"]) for e in d.planted["labels"]["creat_high"]["events"]}
    creat = ranges.lookup("creatinine")
    for r in rows:
        if r["itemid"] != "90001":
            continue
        v = float(r["valuenum"])
        positive = r["subject_id"] in d.planted["labels"]["creat_high"]["positive"] and (r["subject_id"], v) in planted
        assert (v > creat.high) if positive else (creat.low <= v <= creat.high), r
    ages = [float(r["anchor_age"]) for r in csv.DictReader(open(d.root / "hosp/patients.csv"))]
    assert all(18 <= a <= 90 and a == int(a) for a in ages)


def test_every_range_cites_a_source():
    assert all(r.source and r.low < r.high for r in ranges.RANGES)


def test_runtime_readers_read_the_dummies(tmp_path):
    """v0.2's runtime readers (the code inside the encoder images) read every dummy, except FLIO, whose reader
    needs the full 256x256x1024 grid (128 MiB); R-73 keeps dummy images under 1 MiB. Read-only import."""
    spec = importlib.util.spec_from_file_location("v02_contract", REPO / "perception/runtime/contract.py")
    rt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rt)
    failed = {}
    for fid in sorted(rt._READERS):
        root = (tmp_path / fid).resolve()
        p = make_dummy(fam(fid), SEED, root)
        try:
            rt.read_family(fid, rt.resolve_path(p.name, root), data_root=root)
        except Exception as e:  # noqa: BLE001
            failed[fid] = str(e)
    assert set(failed) == {"flio-tcspc-256x256x1024bin-u16"}, failed


def test_all_families_generate_quickly(tmp_path):
    import neurokit2  # noqa: F401 - the import itself (about 4 s) is not generation time

    t = time.perf_counter()
    for fid in sorted(families.load_registry(REPO)):
        make_dummy(fam(fid), SEED, tmp_path)
    assert time.perf_counter() - t < 10


ENCODER_INPUTS = {
    "perception/encoders/eog-2ch-200hz-uv/wav2sleep-eog/testdata": "eog-2ch-200hz-uv",
    "perception/encoders/psg-cardiorespiratory-4ch-200hz-mixed/wav2sleep/testdata": "psg-cardiorespiratory-4ch-200hz-mixed",
}


@pytest.mark.parametrize("folder, fid", ENCODER_INPUTS.items())
def test_replaced_encoder_inputs(folder, fid, tmp_path):
    """R-75: the two unpublishable inputs are generated, conform, and regenerate byte for byte."""
    d = REPO / folder
    prov = (d / "PROVENANCE.md").read_text(encoding="utf-8")
    assert "is generated" in prov and "HSP" not in prov and "DREAMT" not in prov and "I0006" not in prov
    assert conforms(fam(fid), d / "input.edf") == []
    again = make_dummy(fam(fid), 2026, tmp_path, "input", subject="DUMMY-1")
    assert again.read_bytes() == (d / "input.edf").read_bytes()
    x = next(iter(edf(d / "input.edf").values()))
    assert len(x[0]) >= 2 * 30 * x[1]  # wav2sleep needs two whole epochs


def test_no_provenance_names_hsp_or_dreamt():
    for p in (REPO / "perception").rglob("PROVENANCE.md"):
        text = p.read_text(encoding="utf-8")
        assert "DREAMT" not in text and "bdsp.io/content/PSG" not in text, p
