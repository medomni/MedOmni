"""BiomedCLIP embeddings and fixed text similarities."""
import json
from pathlib import Path
import numpy as np
import torch
import open_clip
from open_clip.factory import _MODEL_CONFIGS
from open_clip.tokenizer import HFTokenizer
from PIL import Image
from medomni.perception.runtime import Degraded, labels, embedding
FAMILY = 'cxr-radiograph-2d'
_model = _transform = _text = None

def load():
    global _model, _transform, _text
    root = Path(__file__).parent/'assets'
    config = json.loads((root/'biomedclip/open_clip_config.json').read_text())
    config['model_cfg']['text_cfg']['hf_model_name'] = str(root/'biomedbert')
    _MODEL_CONFIGS['medomni_biomedclip'] = config['model_cfg']
    _model, _, _transform = open_clip.create_model_and_transforms('medomni_biomedclip',
        pretrained=str(root/'biomedclip/open_clip_pytorch_model.bin'),pretrained_hf=False,
        image_mean=config['preprocess_cfg']['mean'],image_std=config['preprocess_cfg']['std'])
    _model.eval()
    tokenizer = HFTokenizer(str(root/'biomedbert'),context_length=256)
    with torch.inference_mode():
        _text = _model.encode_text(tokenizer(['a normal chest X-ray','a chest X-ray with pneumonia']),normalize=True)

def encode(sample, options):
    if min(sample['pixels'].shape)<32 or np.ptp(sample['pixels'])==0:
        raise Degraded('chest image is too small or has no contrast')
    tensor = _transform(Image.fromarray(sample['pixels']).convert('RGB'))[None]
    with torch.inference_mode():
        vector = _model.encode_image(tensor,normalize=True)
        scores = (vector@_text.T)[0].tolist()
    sample['notes'].append('grayscale replicated to RGB; upstream BiomedCLIP resize, crop and normalization applied')
    return [embedding(vector[0].tolist()),labels([dict(label=n,value=v) for n,v in zip(
        ['normal_prompt_similarity','pneumonia_prompt_similarity'],scores)],'score')]
