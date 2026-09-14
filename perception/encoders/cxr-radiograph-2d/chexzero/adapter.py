"""CheXzero positive/negative prompt inference."""
import sys
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from torchvision.transforms import functional as TF, InterpolationMode
from contract import Degraded, labels
sys.path.insert(0,str(Path(__file__).parent/'assets'))
import clip
from model import build_model
FAMILY = 'cxr-radiograph-2d'
CLASSES = ['Atelectasis', 'Cardiomegaly', 'Consolidation', 'Edema', 'Enlarged Cardiomediastinum', 'Fracture', 'Lung Lesion', 'Lung Opacity', 'No Finding', 'Pleural Effusion', 'Pleural Other', 'Pneumonia', 'Pneumothorax', 'Support Devices']
_model = _text = None

def load():
    global _model, _text
    state = torch.load(Path(__file__).parent/'assets/model.pt',map_location='cpu',weights_only=True)
    _model = build_model(state).float().eval()
    with torch.inference_mode():
        tokens = clip.tokenize(CLASSES + ['no '+n for n in CLASSES])
        _text = _model.encode_text(tokens)
        _text /= _text.norm(dim=-1,keepdim=True)

def encode(sample, options):
    pixels = sample['pixels']
    if min(pixels.shape)<32 or np.ptp(pixels)==0:
        raise Degraded('chest image is too small or has no contrast')
    image = Image.fromarray(pixels)
    ratio = 320/max(image.size)
    resized = image.resize(tuple(int(v*ratio) for v in image.size),Image.Resampling.LANCZOS)
    square = Image.new('L',(320,320))
    square.paste(resized,((320-resized.width)//2,(320-resized.height)//2))
    tensor = torch.from_numpy(np.asarray(square).copy()).float()[None].repeat(3,1,1)
    tensor = (tensor-101.48761)/83.43944
    tensor = TF.resize(tensor,[_model.visual.input_resolution]*2,interpolation=InterpolationMode.BICUBIC,antialias=True)
    with torch.inference_mode():
        v = _model.encode_image(tensor[None]);v /= v.norm(dim=-1,keepdim=True)
        scores = (v@_text.T).reshape(2,len(CLASSES)).softmax(dim=0)[0]
    sample['notes'].append('image resized and padded to 320 pixels, normalized, then resized for CheXzero')
    return [labels([dict(label=n,value=float(v)) for n,v in zip(CLASSES,scores)],'score')]
