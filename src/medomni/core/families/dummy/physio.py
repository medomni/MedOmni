"""Signals that look like the signal (part 5b), in physical units, driven by the subject model.

- **Heartbeats** (ECG, pleth, arterial and venous pressure): one beat shape placed at the subject's beat times, so
  every cardiac channel of a subject shares one heart rate. The ECG beat is a sum of Gaussians for P, Q, R, S and T,
  the morphology model of ECGSYN (McSharry et al., IEEE TBME 2003). neurokit2's `ecg_simulate` uses the same model,
  but it takes a constant rate and needs about 0.5 s per minute of signal; placing beats is instant and follows the
  subject's rate through the night.
- **Breathing** (effort belts, flow, impedance, capnography, snoring): neurokit2's `rsp_simulate` at the subject's
  breathing rate.
- **EMG**: neurokit2's `emg_simulate`, with chin tone by stage (lowest in REM) and limb bursts at planted times.
- **EEG**: 1/f background plus each stage's rhythm: alpha in wake, theta in N1, spindles and K-complexes in N2,
  slow waves in N3, theta with sawtooth waves in REM (AASM scoring manual). neurokit2's `eeg_simulate` needs `mne`.
- **EOG**: opposite-sign deflections on the two channels: rapid eye movements in REM, slow rolling in N1, blinks in
  wake.
- **SpO2, pulse rate, body position**: straight from the subject model.
- **iEEG**: background plus planted 80-250 Hz bursts.
"""
from __future__ import annotations

import warnings

import numpy as np

from . import rng
from .subject import EPOCH, Subject

MAX_SECONDS = 300.0
MAX_BYTES = int(0.9 * (1 << 20))


def duration(n_channels: int, fs: float, bytes_per_sample: int = 2) -> float:
    """Whole 30 s epochs, at most 5 minutes, keeping the file under 1 MiB."""
    fit = MAX_BYTES / max(1, n_channels * fs * bytes_per_sample)
    return float(max(EPOCH, min(MAX_SECONDS, (fit // EPOCH) * EPOCH)))


def _t(fs: float, seconds: float) -> np.ndarray:
    return np.arange(int(round(fs * seconds))) / fs


def _place(shape_fn, beats: np.ndarray, t: np.ndarray, delay: float = 0.0) -> np.ndarray:
    out = np.zeros(len(t))
    for b in beats + delay:
        lo, hi = np.searchsorted(t, b - 0.4), np.searchsorted(t, b + 0.7)
        out[lo:hi] += shape_fn(t[lo:hi] - b)
    return out


def ecg_beat(dt: np.ndarray) -> np.ndarray:
    """One PQRST beat in mV, time relative to the R peak (ECGSYN's Gaussians)."""
    waves = ((-0.2, 0.025, 0.15), (-0.03, 0.01, -0.12), (0.0, 0.012, 1.2), (0.03, 0.01, -0.25), (0.25, 0.05, 0.3))
    return sum(a * np.exp(-((dt - mu) ** 2) / (2 * s ** 2)) for mu, s, a in waves)


def pulse_beat(dt: np.ndarray) -> np.ndarray:
    """One pulse wave (0..1): a systolic peak and a smaller diastolic wave."""
    return np.exp(-((dt - 0.12) ** 2) / (2 * 0.06 ** 2)) + 0.4 * np.exp(-((dt - 0.38) ** 2) / (2 * 0.08 ** 2))


LEAD_WEIGHTS = {"i": 0.6, "ii": 1.0, "iii": 0.4, "avr": -0.8, "avl": 0.1, "avf": 0.7, "v1": -0.5, "v2": 0.3,
                "v3": 0.8, "v4": 1.1, "v5": 1.0, "v6": 0.8, "v": 0.9, "mcl": -0.5, "ecg": 1.0}


def ecg(s: Subject, lead: str, fs: float, seconds: float, g) -> np.ndarray:
    t = _t(fs, seconds)
    w = LEAD_WEIGHTS.get(lead.lower(), 1.0)
    return w * _place(ecg_beat, s.beats(seconds), t) + 0.02 * g.standard_normal(len(t))


def pulse(s: Subject, fs: float, seconds: float, low: float, high: float, g) -> np.ndarray:
    t = _t(fs, seconds)
    x = _place(pulse_beat, s.beats(seconds), t, delay=0.2)  # pulse transit time
    x = x / max(x.max(), 1e-9)
    return low + (high - low) * x + 0.003 * (high - low) * g.standard_normal(len(t))


def breathing(s: Subject, fs: float, seconds: float, g, phase: float = 0.0) -> np.ndarray:
    import neurokit2 as nk

    base = round(fs)  # rsp_simulate needs a whole rate (U2.16); resample to non-integer rates
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        x = nk.rsp_simulate(duration=int(np.ceil(seconds)) + 1, sampling_rate=base, respiratory_rate=s.br,
                            random_state=int(g.integers(0, 2 ** 31)))
    x = np.asarray(x, dtype=float)
    n = int(round(fs * seconds))
    if base != fs:
        from scipy.signal import resample

        x = resample(x[: int(round(base * seconds))], n)
    shift = int(phase * fs)
    return np.roll(x, shift)[:n]


def _phase(x: np.ndarray) -> np.ndarray:
    """Inspiration (True) or expiration, with hysteresis so noise near the middle never splits a breath."""
    mid, band = float(np.median(x)), 0.25 * float(np.std(x))
    out, state = np.zeros(len(x), dtype=bool), bool(x[0] > mid)
    for i, v in enumerate(x):
        if state and v < mid - band:
            state = False
        elif not state and v > mid + band:
            state = True
        out[i] = state
    return out


def emg(s: Subject, fs: float, seconds: float, g, limb: bool) -> np.ndarray:
    import neurokit2 as nk

    t = _t(fs, seconds)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        noise = np.asarray(nk.emg_simulate(duration=int(np.ceil(seconds)), sampling_rate=round(fs), burst_number=0,
                                           random_state=int(g.integers(0, 2 ** 31))), dtype=float)[: len(t)]
    noise = noise / max(np.std(noise), 1e-9)
    if limb:
        env = np.full(len(t), 0.05)
        for m in s.leg_movements:
            env[(t >= m) & (t < m + 1.5)] = 1.0
    else:
        tone = {"W": 1.0, "N1": 0.6, "N2": 0.4, "N3": 0.35, "REM": 0.08}
        env = np.array([tone[s.stage(x)] for x in t])
    return 20.0 * env * noise  # uV


def _pink(n: int, g) -> np.ndarray:
    f = np.fft.rfftfreq(n)
    spec = (g.standard_normal(len(f)) + 1j * g.standard_normal(len(f))) / np.maximum(f, 1 / n) ** 0.5
    x = np.fft.irfft(spec, n)
    return x / max(np.std(x), 1e-9)


def eeg(s: Subject, fs: float, seconds: float, g, channel: str = "") -> np.ndarray:
    t = _t(fs, seconds)
    x = 5.0 * _pink(len(t), g)
    for i, stage in enumerate(s.stages(seconds) or ["W"]):
        lo, hi = int(i * EPOCH * fs), int(min(len(t), (i + 1) * EPOCH * fs))
        tt = t[lo:hi] - t[lo]
        if stage == "W":
            x[lo:hi] += 20 * np.sin(2 * np.pi * 10 * tt + g.uniform(0, 6.28))
        elif stage == "N1":
            x[lo:hi] += 15 * np.sin(2 * np.pi * 6 * tt + g.uniform(0, 6.28))
        elif stage == "N2":
            x[lo:hi] += 10 * np.sin(2 * np.pi * 5 * tt)
            for c in g.uniform(1, EPOCH - 3, size=3):  # spindles: 12-14 Hz, about 1 s
                w = np.exp(-((tt - c) ** 2) / (2 * 0.25 ** 2))
                x[lo:hi] += 25 * w * np.sin(2 * np.pi * 13 * tt)
            k = g.uniform(3, EPOCH - 3)  # one K-complex: a sharp negative then a positive wave
            x[lo:hi] += -80 * np.exp(-((tt - k) ** 2) / (2 * 0.1 ** 2)) + 50 * np.exp(-((tt - k - 0.35) ** 2) / (2 * 0.15 ** 2))
        elif stage == "N3":
            x[lo:hi] += 75 * np.sin(2 * np.pi * 1.0 * tt + g.uniform(0, 6.28))
        else:  # REM: low-voltage theta with sawtooth bursts
            x[lo:hi] += 10 * np.sin(2 * np.pi * 6 * tt)
            saw = 2 * ((3 * tt) % 1) - 1
            x[lo:hi] += 12 * saw * (np.sin(2 * np.pi * 0.2 * tt) > 0.5)
    return x


def eog(s: Subject, fs: float, seconds: float, g, sign: float) -> np.ndarray:
    t = _t(fs, seconds)
    x = 3.0 * g.standard_normal(len(t))
    for i, stage in enumerate(s.stages(seconds) or ["W"]):
        lo, hi = int(i * EPOCH * fs), int(min(len(t), (i + 1) * EPOCH * fs))
        tt = t[lo:hi] - t[lo]
        if stage == "REM":
            for c in g.uniform(0, EPOCH - 1, size=6):  # rapid eye movements: fast steps out and back
                x[lo:hi] += 120 * ((tt > c) & (tt < c + 0.4))
        elif stage == "N1":
            x[lo:hi] += 80 * np.sin(2 * np.pi * 0.3 * tt)  # slow rolling
        elif stage == "W":
            for c in g.uniform(0, EPOCH - 1, size=4):  # blinks
                x[lo:hi] += 150 * np.exp(-((tt - c) ** 2) / (2 * 0.08 ** 2))
    return sign * x


def ieeg(s: Subject, fs: float, seconds: float, g) -> np.ndarray:
    t = _t(fs, seconds)
    x = 20 * _pink(len(t), g)
    for c in g.uniform(1, seconds - 1, size=int(seconds // 10)):
        w = np.exp(-((t - c) ** 2) / (2 * 0.02 ** 2))
        x += 15 * w * np.sin(2 * np.pi * g.uniform(80, 250) * t)
    return x


def snore(s: Subject, fs: float, seconds: float, g) -> np.ndarray:
    t = _t(fs, seconds)
    insp = np.clip(-np.gradient(breathing(s, fs, seconds, g)), 0, None)
    deep = np.array([1.0 if s.stage(x) in ("N2", "N3") else 0.2 for x in t])
    return 50 * deep * insp / max(insp.max(), 1e-9) * g.standard_normal(len(t))


ECG_NAMES = set(LEAD_WEIGHTS)
PULSE = {"pleth": (0.0, 1.0)}
BREATH = {"thorax", "thx", "abdomen", "abd", "nasal-pressure", "derived-flow", "thermistor", "resp"}


def signal(family, channel: str, s: Subject, fs: float, seconds: float, seed: int) -> np.ndarray | None:
    """The physical signal of one channel, or None when the family stays at the format level."""
    g = rng(seed, family.id, channel, "physio")
    c, fid = channel.lower(), family.id
    if fid.startswith("actigraphy"):
        return None
    if fid.startswith("eeg"):
        return eeg(s, fs, seconds, g, c)
    if fid.startswith("eog"):
        return eog(s, fs, seconds, g, 1.0 if c.startswith("e1") else -1.0)
    if fid.startswith("emg-chin"):
        return emg(s, fs, seconds, g, limb=False)
    if fid.startswith("emg-limb"):
        return emg(s, fs, seconds, g, limb=True)
    if fid.startswith("ieeg"):
        return ieeg(s, fs, seconds, g)
    if fid.startswith("snore"):
        return snore(s, fs, seconds, g)
    if fid.startswith("spo2"):
        return s.spo2_at(_t(fs, seconds))
    if fid.startswith("pulse-rate"):
        return s.hr_at(_t(fs, seconds))
    if fid.startswith("body-position"):
        return s.position_at(_t(fs, seconds)).astype(float)
    if fid.startswith("abp"):
        return pulse(s, fs, seconds, s.dbp, s.sbp, g)
    if fid.startswith("pressure-nonarterial"):
        return pulse(s, fs, seconds, {"cvp": 3.0, "pap": 10.0, "icp": 8.0}.get(c, 3.0),
                     {"cvp": 8.0, "pap": 25.0, "icp": 14.0}.get(c, 8.0), g)
    if fid.startswith("capnography"):
        if c == "etco2-waveform":
            insp = _phase(breathing(s, fs, seconds, g))
            return np.where(insp, 1.0, 38.0) + 0.5 * g.standard_normal(int(round(fs * seconds)))
        return 38.0 + 0.5 * g.standard_normal(int(round(fs * seconds)))  # end-tidal or transcutaneous level
    if c in ECG_NAMES:
        mv = ecg(s, c, fs, seconds, g)
        return mv * (1000.0 if (family.protocol.units or "").lower() == "uv" or fid.startswith("psg") else 1.0)
    if c in PULSE or fid.startswith("ppg"):
        return pulse(s, fs, seconds, 0.0, 1.0, g)
    if c in BREATH or fid.startswith(("resp", "psg")):
        x = breathing(s, fs, seconds, g, phase=0.15 if c in ("abdomen", "abd") else 0.0)
        if c == "derived-flow" or c == "nasal-pressure":
            x = np.gradient(x) * fs / max(s.br / 60, 1e-3)
        if fid.startswith("resp-impedance"):
            return 500.0 + 2.0 * x
        return x
    return None
