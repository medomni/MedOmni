"""Five-grade diabetic retinopathy probabilities from RETFound fine-tuned on APTOS-2019."""
import os
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from contract import Degraded, labels

FAMILY = 'fundus-photography-2d'
# Head index order = the training folders sorted by name: anodr, bmilddr, cmoderatedr,
# dseveredr, eproliferativedr (RETFound BENCHMARK.md APTOS2019 split).
GRADES = ('dr_none', 'dr_mild', 'dr_moderate', 'dr_severe', 'dr_proliferative')


def load():
    from models_vit import RETFound_mae
    path = Path(os.environ.get('RETFOUND_DR_WEIGHTS', '/opt/weights/model.pth'))
    state = torch.load(path, map_location='cpu', weights_only=True, mmap=True)
    model = RETFound_mae(global_pool=True, num_classes=len(GRADES))
    model.load_state_dict(state, strict=True)
    return model.eval()


def encode(sample, options):
    pixels = sample['pixels']
    if pixels.ndim != 3 or pixels.shape[2] != 3 or pixels.dtype != np.uint8:
        raise Degraded('RETFound DR requires an eight-bit colour fundus image')
    transform = transforms.Compose([
        transforms.Resize(256, interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.CenterCrop(224), transforms.ToTensor(),
        transforms.Normalize((.485, .456, .406), (.229, .224, .225)),
    ])
    with torch.inference_mode():
        # RETFound's forward_features predates timm's attn_mask argument; pool, then head.
        model = options['_model']
        logits = model.head(model.forward_features(transform(Image.fromarray(pixels)).unsqueeze(0))).reshape(-1)
    probs = torch.softmax(logits, dim=0)
    if probs.shape != (len(GRADES),) or not torch.isfinite(probs).all():
        raise RuntimeError('RETFound DR produced invalid probabilities')
    values = [float(p) for p in probs]
    items = [dict(label=name, value=value) for name, value in zip(GRADES, values)]
    items.append(dict(label='dr_referable', value=sum(values[2:])))
    return [labels(items, 'probability')]
