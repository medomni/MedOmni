"""Named macular findings per OCT volume from KD-OCT (EfficientNet-B2, Kermany OCT2017).

The checkpoint classifies one Spectralis B-scan into CNV, DME, drusen or normal. Every B-scan of
the volume is first resampled to the Spectralis pixel geometry the model was trained on, using the
file's own pixel spacing, and cropped to 496 rows around the retina. The response reports the
central B-scan's probabilities, the mean and maximum over B-scans, and the share of B-scans on
which each finding ranks first.
"""
import os
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from medomni.perception.runtime import Degraded, labels, text

FAMILY = 'oct-volume-raster-mono8-3d'
# Head index order = the training folders sorted by name (KD-OCT Student-Training/UCSD/data/dataset.py).
CLASSES = ('cnv', 'dme', 'drusen', 'normal')
NAMES = {'cnv': 'choroidal neovascularisation', 'dme': 'diabetic macular oedema',
         'drusen': 'drusen', 'normal': 'normal'}
SPECTRALIS_MM = (0.003872, 0.0117)   # axial, lateral mm per pixel of the Kermany (Spectralis) training scans
ROWS = 496                           # Spectralis B-scan depth
CONFIDENT = 0.6
BATCH = 16
TRANSFORM = transforms.Compose([
    transforms.Resize((384, 384)), transforms.ToTensor(),
    transforms.Normalize((.485, .456, .406), (.229, .224, .225)),
])


def load():
    import timm
    path = Path(os.environ.get('KDOCT_WEIGHTS', '/opt/weights/model.pth'))
    model = timm.create_model('efficientnet_b2', num_classes=len(CLASSES), pretrained=False)
    model.load_state_dict(torch.load(path, map_location='cpu', weights_only=True), strict=True)
    return model.eval()


def _to_spectralis(plane, spacing):
    if spacing:
        height = max(1, round(plane.shape[0] * spacing[0] / SPECTRALIS_MM[0]))
        width = max(1, round(plane.shape[1] * spacing[1] / SPECTRALIS_MM[1]))
        plane = np.asarray(Image.fromarray(np.ascontiguousarray(plane)).resize((width, height), Image.BICUBIC))
    # The retina is the brightest band: centre a 496-row window on the brightest 60-row stretch.
    rows = plane.astype(np.float64).mean(axis=1)
    centre = int(np.argmax(np.convolve(rows, np.ones(60) / 60, 'same')))
    top = min(max(0, centre - ROWS // 2), max(0, plane.shape[0] - ROWS))
    plane = plane[top:top + ROWS]
    if plane.shape[0] < ROWS:
        plane = np.pad(plane, ((0, ROWS - plane.shape[0]), (0, 0)))
    return plane


def _probabilities(model, planes, spacing):
    batch = torch.stack([TRANSFORM(Image.fromarray(_to_spectralis(p, spacing)).convert('RGB')) for p in planes])
    with torch.inference_mode():
        return torch.softmax(model(batch), dim=1)


def encode(sample, options):
    volume = sample['pixels']
    if volume.ndim != 3 or volume.dtype != np.uint8:
        raise Degraded('KD-OCT requires a stack of eight-bit B-scans')
    spacing = (sample.get('acquisition') or {}).get('pixel_spacing_mm')
    if not spacing:
        sample['notes'].append('No pixel spacing in the file; B-scans are not resampled to the training geometry.')
    n_frames = int(volume.shape[0])
    usable = [i for i in range(n_frames) if int(volume[i].max()) != int(volume[i].min())]
    if not usable:
        raise Degraded('every B-scan is blank')
    if len(usable) < n_frames:
        sample['notes'].append(f'{n_frames - len(usable)} blank B-scan(s) skipped')
    model = options['_model']
    probs = torch.cat([_probabilities(model, volume[usable[i:i + BATCH]], spacing)
                       for i in range(0, len(usable), BATCH)])
    if probs.shape != (len(usable), len(CLASSES)) or not torch.isfinite(probs).all():
        raise RuntimeError('KD-OCT produced invalid probabilities')
    # The central B-scan is the stored middle frame; the nearest non-blank one if it is blank.
    centre = min(range(len(usable)), key=lambda k: (abs(usable[k] - (n_frames - 1) / 2), usable[k]))
    central = [float(p) for p in probs[centre]]
    mean = [float(p) for p in probs.mean(dim=0)]
    peak = [float(p) for p in probs.max(dim=0).values]
    top = probs.argmax(dim=1)
    share = [float((top == k).sum()) / len(usable) for k in range(len(CLASSES))]
    items = ([dict(label=f'central_{c}', value=v) for c, v in zip(CLASSES, central)]
             + [dict(label=f'mean_{c}', value=v) for c, v in zip(CLASSES, mean)]
             + [dict(label=f'max_{c}', value=v) for c, v in zip(CLASSES, peak)])
    shares = [dict(label=f'top_share_{c}', value=v) for c, v in zip(CLASSES, share)]
    ranked = sorted(range(len(CLASSES)), key=lambda k: -central[k])
    counts = sorted(range(len(CLASSES)), key=lambda k: -share[k])
    confident = float(probs.max(dim=1).values.ge(CONFIDENT).float().mean())
    summary = ('Central B-scan: ' + '; '.join(f'{NAMES[CLASSES[k]]} {central[k]:.2f}' for k in ranked[:3])
               + ('' if central[ranked[0]] >= CONFIDENT else ' (uncertain)')
               + f'. Top finding across {len(usable)} B-scans: '
               + ', '.join(f'{NAMES[CLASSES[k]]} on {round(share[k] * len(usable))}' for k in counts if share[k] > 0)
               + f'; {confident:.0%} of B-scans read with probability >= {CONFIDENT}.')
    return [labels(items, 'probability'), labels(shares, 'score'), text(summary)]
