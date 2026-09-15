"""BayesBeat AF inference on published 25-second PPG segments."""
import sys
from pathlib import Path
import numpy as np
import torch
from scipy.signal import butter, resample_poly, sosfiltfilt
from contract import BadRequest, Degraded, labels

ROOT = Path(__file__).parent / "assets"
sys.path.insert(0, str(ROOT))
from models.BayesBeat import Bayesian_Deepbeat

FAMILY = "ppg-waveform-uncal"
_model = None


def load():
    global _model
    _model = Bayesian_Deepbeat()
    checkpoint = torch.load(ROOT / "saved_model/bayesbeat_cpu.pt", map_location="cpu",
                            weights_only=False)
    _model.load_state_dict(checkpoint["state_dict"])
    _model.eval()
    return _model


def encode(sample, options):
    unknown = set(options) - {"start_sec", "samples", "_model"}
    if unknown:
        raise BadRequest("unknown BayesBeat option(s): " + ", ".join(sorted(unknown)))
    start = options.get("start_sec", 0)
    draws = options.get("samples", 15)
    if isinstance(start, bool) or not isinstance(start, (int, float)) or start < 0:
        raise BadRequest("start_sec must be a non-negative number")
    if isinstance(draws, bool) or not isinstance(draws, int) or not 2 <= draws <= 100:
        raise BadRequest("samples must be an integer from 2 through 100")
    rate = sample["rate_hz"]
    values = np.asarray(sample["channels"]["pleth"], dtype=float)
    first, count = round(start * rate), round(25 * rate)
    values = values[first:first + count]
    if len(values) != count:
        raise Degraded("BayesBeat requires a complete 25-second PPG segment")
    if not np.isfinite(values).all() or np.ptp(values) == 0:
        raise Degraded("PPG segment is non-finite or flat")
    filtered = sosfiltfilt(butter(3, [0.5, 4.0], btype="bandpass", fs=rate, output="sos"), values)
    signal = resample_poly(filtered, 32, round(rate))
    if len(signal) != 800:
        signal = np.interp(np.linspace(0, len(signal) - 1, 800), np.arange(len(signal)), signal)
    low, high = float(signal.min()), float(signal.max())
    if high <= low:
        raise Degraded("filtered PPG segment is flat")
    tensor = torch.tensor(((signal - low) / (high - low))[None, None], dtype=torch.float32)
    model = options.get("_model") or _model
    if model is None:
        model = load()
    with torch.inference_mode():
        repeated = torch.repeat_interleave(tensor, draws, dim=0)
        logits, _ = model(repeated)
        probabilities = torch.softmax(logits, dim=1).reshape(1, draws, 2).numpy()
    mean = probabilities.mean(axis=1)[0]
    centered = probabilities[0] - mean
    epistemic = np.diag(centered.T @ centered / draws)
    aleatoric = np.diag(np.diag(mean) - probabilities[0].T @ probabilities[0] / draws)
    sample["notes"].append(
        f"selected [{start:g},{start + 25:g}) seconds; 0.5-4 Hz filter; resampled to 32 Hz; min-max scaled")
    return [labels([
        {"label": "non_af", "value": float(mean[0])},
        {"label": "af", "value": float(mean[1])},
        {"label": "non_af_epistemic", "value": float(epistemic[0])},
        {"label": "af_epistemic", "value": float(epistemic[1])},
        {"label": "non_af_aleatoric", "value": float(aleatoric[0])},
        {"label": "af_aleatoric", "value": float(aleatoric[1])},
    ], "probability")]
