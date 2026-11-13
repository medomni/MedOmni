"""wav2sleep cardiorespiratory sleep-stage inference."""
from pathlib import Path
import numpy as np
import torch
from scipy.signal import resample_poly
from medomni.perception.runtime import BadRequest, Degraded, events
from wav2sleep import load_model

FAMILY = "psg-cardiorespiratory-4ch-200hz-mixed"
LABELS = ("Wake", "N1+N2", "N3", "REM")
SIGNALS = {"ecg": ("ECG", 128, 750), "pleth": ("PPG", 128, 750),
           "abd": ("ABD", 16, 375), "thx": ("THX", 16, 375)}

def load():
    return load_model(str(Path(__file__).parent / "assets/model"), device="cpu")

def encode(sample, options):
    unknown = set(options) - {"_model", "max_epochs"}
    if unknown:
        raise BadRequest("unknown wav2sleep option(s): " + ", ".join(sorted(unknown)))
    max_epochs = options.get("max_epochs", 1200)
    if isinstance(max_epochs, bool) or not isinstance(max_epochs, int) or not 1 <= max_epochs <= 1200:
        raise BadRequest("max_epochs must be an integer from 1 through 1200")
    epochs = min(sample["n_samples"] // 6000, max_epochs)
    if epochs < 2:
        raise Degraded("wav2sleep needs at least two complete 30-second epochs")
    signals = {}
    for source, (target, up, down) in SIGNALS.items():
        values = np.asarray(sample["channels"][source][:epochs * 6000], dtype=np.float32)
        if not np.isfinite(values).all() or np.ptp(values) == 0:
            raise Degraded(f"{source} contains missing values or is flat")
        values = resample_poly(values, up, down).astype(np.float32)
        values = (values - values.mean()) / max(float(values.std()), 1e-6)
        signals[target] = torch.from_numpy(values).unsqueeze(0)
    with torch.inference_mode():
        probabilities = torch.softmax(options["_model"](signals), dim=-1)[0].cpu().numpy()
    items = []
    for index, scores in enumerate(probabilities):
        items.append({"label": LABELS[int(scores.argmax())], "t_start": index * 30.0,
                      "t_end": (index + 1) * 30.0, "score": float(scores.max())})
    sample["notes"].append("ECG and PPG resampled to 1024, effort signals to 256 samples per epoch; each signal globally z-scored")
    return [events(items)]
