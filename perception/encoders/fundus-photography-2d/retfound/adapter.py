"""Expose the pretrained RETFound MAE class token without a disease head."""
import hashlib
import os
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from medomni.perception.runtime import Degraded, embedding

FAMILY = 'fundus-photography-2d'
WEIGHT_SHA256 = 'e1e4f66a1b792eeb6e2efaf158f33be35c8255f36b3d17ed67cd5129da246485'


def load():
    from models_vit import RETFound_mae
    path = Path(os.environ.get('RETFOUND_WEIGHTS', '/opt/retfound/RETFound_mae_natureCFP.pth'))
    with path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != WEIGHT_SHA256:
            raise RuntimeError('RETFound checkpoint checksum does not match the card')
    # The hash above restricts pickle loading to the pinned official checkpoint.
    checkpoint = torch.load(path, map_location='cpu', weights_only=False, mmap=True)
    state = checkpoint['model']
    # MAE reconstruction parameters and any classification head are not used.
    state = {key: value for key, value in state.items()
             if not key.startswith(('decoder_', 'head.')) and key != 'mask_token'}
    model = RETFound_mae(global_pool=False, num_classes=0)
    model.load_state_dict(state, strict=True)
    return model.eval()


def encode(sample, options):
    pixels = sample['pixels']
    if pixels.ndim != 3 or pixels.shape[2] != 3 or pixels.dtype != np.uint8:
        raise Degraded('RETFound CFP requires an eight-bit colour fundus image')
    transform = transforms.Compose([
        transforms.Resize(256, interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.CenterCrop(224), transforms.ToTensor(),
        transforms.Normalize((.485, .456, .406), (.229, .224, .225)),
    ])
    with torch.inference_mode():
        vector = options['_model'].forward_features(transform(Image.fromarray(pixels)).unsqueeze(0))[0]
    if vector.shape != (1024,) or not torch.isfinite(vector).all():
        raise RuntimeError('RETFound produced an invalid embedding')
    return [embedding(vector.tolist())]
