"""A diabetic retinopathy severity score for a colour fundus photograph.

An EfficientNet-B0 fine-tuned on Aptos, EyePACS, DDR and IDRiD, used as it is:
no further training and no probe. The family's other encoder returns RETFound's
class token, which is a representation and not a finding; this one returns a
number on the scale clinicians grade with.

**The head is a regressor, not a classifier.** Its checkpoint declares one
output, and the published metric is quadratic-weighted kappa — the model was
trained to place an image on the 0..4 International Clinical Diabetic
Retinopathy scale rather than to choose between five labels. So the score is
reported as it comes, and the nearest whole grade is reported beside it. The
response carries no class probabilities, because the model produces none, and
inventing them from one number would be inventing confidence.

Card: card.yaml   Contract: perception/spec/container-api.md §5
"""
import os

import numpy as np
import torch
from PIL import Image

from medomni.perception.runtime import Degraded, labels

FAMILY = "fundus-photography-2d"

WEIGHTS = os.environ.get("DR_GRADE_WEIGHTS", "/opt/weights/model.safetensors")

# The published configuration, from the checkpoint's own config.json:
# efficientnet_b0 with a single output, ImageNet statistics, bicubic
# interpolation, and a centre crop covering 87.5 percent of the frame.
ARCHITECTURE = "efficientnet_b0"
N_OUTPUTS = 1
INPUT_SIZE = 224
CROP_PCT = 0.875
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)

# The International Clinical Diabetic Retinopathy severity scale, which is what
# the four training sets grade on. The names are the scale's, not the model's:
# the model emits a position on it.
GRADE_NAMES = ("no-dr", "mild", "moderate", "severe", "proliferative")
GRADE_MIN, GRADE_MAX = 0.0, 4.0
PRECISION = 4


def load():
    """Build the architecture and read the checkpoint once, at start."""
    import timm
    from safetensors.torch import load_file

    # pretrained=False: the ImageNet weights timm would fetch are replaced by
    # every tensor below, and an image built to run offline cannot fetch them.
    model = timm.create_model(ARCHITECTURE, pretrained=False, num_classes=N_OUTPUTS)
    model.load_state_dict(load_file(WEIGHTS), strict=True)
    if model.classifier.out_features != N_OUTPUTS:
        raise RuntimeError(f"the head emits {model.classifier.out_features} value(s), "
                           f"expected {N_OUTPUTS}")
    model.eval()
    return model


def _preprocess(pixels):
    """Resize by crop_pct, centre crop, scale and normalise, as the config declares."""
    image = Image.fromarray(pixels)
    short = int(round(INPUT_SIZE / CROP_PCT))
    width, height = image.size
    scale = short / min(width, height)
    image = image.resize((max(1, round(width * scale)), max(1, round(height * scale))),
                         Image.BICUBIC)
    width, height = image.size
    left, top = (width - INPUT_SIZE) // 2, (height - INPUT_SIZE) // 2
    image = image.crop((left, top, left + INPUT_SIZE, top + INPUT_SIZE))
    array = np.asarray(image, dtype=np.float32) / 255.0
    array = (array - np.asarray(MEAN, dtype=np.float32)) / np.asarray(STD, dtype=np.float32)
    return torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)


def encode(sample, options):
    pixels = sample["pixels"]
    if pixels.ndim != 3 or pixels.shape[2] != 3 or pixels.dtype != np.uint8:
        raise Degraded("this encoder reads a colour fundus photograph; the decoder "
                       "returned a single plane, which is an infrared frame and a "
                       "different acquisition")
    if int(pixels.max()) == int(pixels.min()):
        raise Degraded("the photograph is blank; every pixel has the same value")
    if min(pixels.shape[:2]) < INPUT_SIZE:
        raise Degraded(f"the photograph is {pixels.shape[0]}x{pixels.shape[1]}; below "
                       f"{INPUT_SIZE} on a side the crop would enlarge detail the camera "
                       "never captured")

    with torch.no_grad():
        score = float(options["_model"](_preprocess(pixels))[0, 0])
    if not np.isfinite(score):
        raise Degraded("the model produced a non-finite score")

    # Clamping is reporting, not correcting: a score outside the scale is the
    # model saying something the scale cannot express, and the note says so.
    clamped = min(max(score, GRADE_MIN), GRADE_MAX)
    if clamped != score:
        sample["notes"].append(
            f"the raw score {score:.4f} lies outside the 0..4 scale and was clamped "
            "for the grade; dr_severity_score reports what the model emitted")
    grade = int(round(clamped))

    sample["notes"].append(f"nearest whole grade is {grade} ({GRADE_NAMES[grade]}); "
                           "the model emits a position on the scale, not a class")
    return [labels([{"label": "dr_severity_score", "value": round(score, PRECISION)},
                    {"label": "dr_grade_nearest", "value": float(grade)}],
                   scale="score")]
